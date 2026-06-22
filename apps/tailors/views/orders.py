# apps/tailors/views/orders.py
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema

from apps.orders.models import Order
from apps.tailors.serializers.orders import TailorUpdateOrderStatusSerializer, TailorAddMeasurementsSerializer
from apps.orders.serializers import OrderStatusUpdateResponseSerializer, OrderSerializer
from zthob.utils import api_response


from apps.tailors.permissions import IsShopStaff


def _get_rider_or_404(rider_id):
    from apps.accounts.models import CustomUser
    return get_object_or_404(CustomUser, id=rider_id, role='RIDER')


def _assign_measurement_rider(order, rider):
    order.measurement_rider = rider
    order.assigned_rider = rider
    order.rider = rider
    order.save(update_fields=[
        'measurement_rider',
        'assigned_rider',
        'rider',
        'updated_at',
    ])


def _assign_delivery_rider(order, rider):
    order.delivery_rider = rider
    order.assigned_rider = rider
    order.rider = rider
    if order.rider_status == 'measurement_taken':
        order.rider_status = 'none'
        update_fields = ['delivery_rider', 'assigned_rider', 'rider', 'rider_status', 'updated_at']
    else:
        update_fields = ['delivery_rider', 'assigned_rider', 'rider', 'updated_at']
    order.save(update_fields=update_fields)


def _open_delivery_assignment(order):
    order.delivery_rider = None
    order.assigned_rider = None
    order.rider = None
    if order.rider_status == 'measurement_taken':
        order.rider_status = 'none'
        update_fields = ['delivery_rider', 'assigned_rider', 'rider', 'rider_status', 'updated_at']
    else:
        update_fields = ['delivery_rider', 'assigned_rider', 'rider', 'updated_at']
    order.save(update_fields=update_fields)


def _notify_assigned_rider(order, rider_id):
    try:
        from apps.notifications.services import NotificationService
        NotificationService.send_new_order_broadcast(order, assigned_rider_id=rider_id)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to send assigned rider notification: {str(e)}")


def _can_assign_delivery_rider(order, new_status=None):
    return order.service_mode == 'home_delivery' and (
        order.status == 'ready_for_delivery' or new_status == 'ready_for_delivery'
    )


class TailorAcceptOrderView(APIView):
    """Tailor accepts an order"""
    permission_classes = [IsAuthenticated, IsShopStaff]
    required_employee_permission = 'can_manage_orders'

    
    @extend_schema(
        request=TailorUpdateOrderStatusSerializer,  # Reuse the same serializer now
        responses={200: OrderSerializer},
        summary="Accept order",
        description="Tailor accepts an order. Sets tailor_status to 'accepted' and typically updates main status to 'confirmed'. Can also assign a specific rider.",
        tags=["Tailor Orders"],
        parameters=[
            {
                'name': 'order_id',
                'in': 'path',
                'required': True,
                'description': 'Order ID to accept',
                'schema': {'type': 'integer'}
            }
        ]
    )
    def post(self, request, order_id):
        """Accept order - order_id comes from URL path"""
        order = get_object_or_404(Order, id=order_id)
        
        # Check permissions for this specific order
        self.check_object_permissions(request, order)

        
        rider_assignment_type = request.data.get('rider_assignment_type')
        assigned_rider_id = request.data.get('assigned_rider_id')
        assigned_rider = None
        if assigned_rider_id:
            assigned_rider = _get_rider_or_404(assigned_rider_id)
            if rider_assignment_type == 'delivery':
                return api_response(
                    success=False,
                    message="Delivery rider can only be assigned when marking the order ready for delivery.",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            if rider_assignment_type == 'measurement' and order.all_items_have_measurements:
                return api_response(
                    success=False,
                    message="Measurements already exist for this order. Assign a delivery rider when marking ready for delivery.",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
        
        # Check if already accepted
        if order.tailor_status == 'accepted':
            return api_response(
                success=False,
                message="Order is already accepted",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # Store old tailor_status for notification
        old_tailor_status = order.tailor_status
        
        # Use transition service to update tailor status to 'accepted'
        from apps.orders.services import OrderStatusTransitionService
        
        success, error_msg, updated_order = OrderStatusTransitionService.transition(
            order=order,
            new_tailor_status='accepted',
            user=request.user,
            notes='Tailor accepted the order',
            requested_role='TAILOR'
        )
        
        if not success:
            return api_response(
                success=False,
                message=error_msg,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        order = updated_order

        if assigned_rider and not order.all_items_have_measurements:
            _assign_measurement_rider(order, assigned_rider)
        
        response_serializer = OrderSerializer(order, context={'request': request})
        return api_response(
            success=True,
            message="Order accepted successfully",
            data=response_serializer.data,
            status_code=status.HTTP_200_OK
        )


class TailorUpdateOrderStatusView(APIView):
    """Tailor updates order status"""
    permission_classes = [IsAuthenticated, IsShopStaff]
    required_employee_permission = 'can_manage_orders'

    
    @extend_schema(
        request=TailorUpdateOrderStatusSerializer,
        responses=OrderStatusUpdateResponseSerializer,
        summary="Update order status",
        description="Tailor updates order tailor_status (accepted, in_progress, stitching_started, stitched). You can also use /accept/ endpoint to accept orders.",
        tags=["Tailor Orders"]
    )
    def patch(self, request, order_id):
        order = get_object_or_404(Order, id=order_id)
        
        # Check permissions
        self.check_object_permissions(request, order)

        
        serializer = TailorUpdateOrderStatusSerializer(data=request.data)
        if serializer.is_valid():
            new_tailor_status = serializer.validated_data.get('tailor_status')
            new_status = serializer.validated_data.get('status')
            notes = serializer.validated_data.get('notes', '')
            assigned_rider_id = serializer.validated_data.get('assigned_rider_id')
            rider_assignment_type = serializer.validated_data.get('rider_assignment_type')
            assigned_rider = None
            is_ready_for_delivery_action = new_status == 'ready_for_delivery' or new_tailor_status == 'ready_for_delivery'

            if assigned_rider_id:
                assigned_rider = _get_rider_or_404(assigned_rider_id)
                if not rider_assignment_type:
                    rider_assignment_type = 'delivery' if is_ready_for_delivery_action else 'measurement'

                if rider_assignment_type == 'measurement' and order.all_items_have_measurements:
                    return api_response(
                        success=False,
                        message="Measurements already exist for this order. Assign a delivery rider when marking ready for delivery.",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )

                if rider_assignment_type == 'delivery' and not _can_assign_delivery_rider(order, new_status='ready_for_delivery' if is_ready_for_delivery_action else new_status):
                    return api_response(
                        success=False,
                        message="Delivery rider can only be assigned when the order is ready for delivery.",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
            
            # Special handling: if tailor_status is "ready_for_delivery", map it to main status
            # This allows consistent use of tailor_status field
            if new_tailor_status == 'ready_for_delivery':
                new_status = 'ready_for_delivery'
                new_tailor_status = None  # Don't update tailor_status
            
            # Special handling: if tailor_status is "record_measurements", it's a form trigger
            # We return success but don't perform a state transition
            if new_tailor_status == 'record_measurements':
                response_serializer = OrderStatusUpdateResponseSerializer(order, context={'request': request})
                return api_response(
                    success=True,
                    message="Please record measurements for this order.",
                    data=response_serializer.data,
                    status_code=status.HTTP_200_OK
                )
            
            # Store old tailor_status for notification
            old_tailor_status = order.tailor_status
            
            # Use transition service
            from apps.orders.services import OrderStatusTransitionService
            
            success, error_msg, updated_order = OrderStatusTransitionService.transition(
                order=order,
                new_status=new_status,
                new_tailor_status=new_tailor_status,
                    user=request.user,
                notes=notes,
                requested_role='TAILOR'
            )
            
            if not success:
                return api_response(
                    success=False,
                    message=error_msg,
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            order = updated_order

            if assigned_rider:
                if rider_assignment_type == 'delivery':
                    _assign_delivery_rider(order, assigned_rider)
                else:
                    _assign_measurement_rider(order, assigned_rider)

                if order.tailor_status in ['accepted', 'in_progress', 'stitching_started', 'stitched'] and not new_tailor_status == 'accepted':
                    _notify_assigned_rider(order, assigned_rider_id)
            elif is_ready_for_delivery_action and order.service_mode == 'home_delivery':
                _open_delivery_assignment(order)

            
            # Use lightweight response serializer for status updates
            response_serializer = OrderStatusUpdateResponseSerializer(order, context={'request': request})
            
            # Build success message
            if new_tailor_status and new_status:
                message = f"Order tailor status updated to {order.get_tailor_status_display()} and status updated to {order.get_status_display()}"
            elif new_tailor_status:
                message = f"Order tailor status updated to {order.get_tailor_status_display()}"
            else:
                message = f"Order status updated to {order.get_status_display()}"
            
            return api_response(
                success=True,
                message=message,
                data=response_serializer.data,
                status_code=status.HTTP_200_OK
            )
        
        return api_response(
            success=False,
            message="Failed to update order status",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class TailorAddMeasurementsView(APIView):
    """Tailor adds measurements for orders (especially Walk-In orders)"""
    permission_classes = [IsAuthenticated, IsShopStaff]
    required_employee_permission = 'can_manage_orders'

    
    @extend_schema(
        request=TailorAddMeasurementsSerializer,
        responses={200: OrderSerializer},
        summary="Add measurements",
        description="Tailor adds measurements taken at the shop. Required before stitching can start.",
        tags=["Tailor Orders"]
    )
    def post(self, request, order_id):
        order = get_object_or_404(
            Order.objects.select_related('family_member', 'customer'),
            id=order_id
        )
        
        # Check permissions
        self.check_object_permissions(request, order)

        
        # Verify order type
        if order.order_type not in ['fabric_with_stitching', 'stitching_only', 'measurement_service']:
            return api_response(
                success=False,
                message="Measurements can only be added for stitching and measurement_service orders",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = TailorAddMeasurementsSerializer(data=request.data)
        if serializer.is_valid():
            measurements_data = serializer.validated_data['measurements']
            family_member_id = serializer.validated_data.get('family_member')
            title = serializer.validated_data.get('title')
            
            # Add title to measurements if provided
            if title:
                measurements_data['title'] = title
            
            # Save measurement timestamp
            order.measurement_taken_at = timezone.now()
            
            # Identify the recipient and update profiles/items
            recipient_name = None
            if family_member_id:
                from apps.customers.models import FamilyMember
                family_member = get_object_or_404(FamilyMember, id=family_member_id, user=order.customer)
                family_member.measurements = measurements_data
                family_member.save()
                recipient_name = family_member.name
                
                # Update all items for this family member in this order
                order.order_items.filter(family_member=family_member).update(measurements=measurements_data)
            else:
                # Update customer profile measurements
                from apps.customers.models import CustomerProfile
                profile, created = CustomerProfile.objects.get_or_create(user=order.customer)
                profile.measurements = measurements_data
                profile.save()
                
                # Update all items for the customer in this order
                order.order_items.filter(family_member__isnull=True).update(measurements=measurements_data)
                recipient_name = order.customer.get_full_name() or order.customer.username if order.customer else 'Customer'
            
            # Save order to persist timestamp
            order.save()
            
            # Check if all items now have measurements
            all_measured = order.all_items_have_measurements
            
            # For measurement_service orders, auto-update tailor_status when measurements are complete
            if order.order_type == 'measurement_service' and order.service_mode == 'walk_in':
                if all_measured and order.tailor_status == 'accepted':
                    # Use transition service to update status
                    from apps.orders.services import OrderStatusTransitionService
                    success, error_msg, updated_order = OrderStatusTransitionService.transition(
                        order=order,
                        new_tailor_status='measurements_complete',
                                    user=request.user,
                        notes=f'Measurements recorded for {recipient_name}'
                    )
                    if success:
                        order = updated_order
                    # Note: If transition fails, we still continue - measurements are saved
            
            # Build message
            message = f"Measurements saved for {recipient_name}."
            if all_measured:
                if order.order_type == 'measurement_service':
                    message += " Measurement service completed."
                else:
                    message += " You can now proceed to stitching."
            
            # Return updated order
            response_serializer = OrderSerializer(order, context={'request': request})
            return api_response(
                success=True,
                message=message,
                data=response_serializer.data,
                status_code=status.HTTP_200_OK
            )
        
        return api_response(
            success=False,
            message="Failed to save measurements",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )
