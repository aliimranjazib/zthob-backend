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


class TailorAcceptOrderView(APIView):
    """Tailor accepts an order"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        request=None,
        responses={200: OrderSerializer},
        summary="Accept order",
        description="Tailor accepts an order. Sets tailor_status to 'accepted' and typically updates main status to 'confirmed'.",
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
        if request.user.role != 'TAILOR':
            return api_response(
                success=False,
                message="Only tailors can access this endpoint",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        order = get_object_or_404(Order, id=order_id)
        
        # Verify tailor has access
        if order.tailor != request.user:
            return api_response(
                success=False,
                message="You don't have access to this order",
                status_code=status.HTTP_403_FORBIDDEN
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
            user_role='TAILOR',
            user=request.user,
            notes='Tailor accepted the order'
        )
        
        if not success:
            return api_response(
                success=False,
                message=error_msg,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        order = updated_order
        
        # Send push notification for tailor acceptance
        try:
            from apps.notifications.services import NotificationService
            NotificationService.send_tailor_status_notification(
                order=order,
                old_tailor_status=old_tailor_status,
                new_tailor_status='accepted',
                changed_by=request.user
            )
        except Exception as e:
            # Log error but don't fail the assignment
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send tailor acceptance notification: {str(e)}")
        
        response_serializer = OrderSerializer(order, context={'request': request})
        return api_response(
            success=True,
            message="Order accepted successfully",
            data=response_serializer.data,
            status_code=status.HTTP_200_OK
        )


class TailorUpdateOrderStatusView(APIView):
    """Tailor updates order status"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        request=TailorUpdateOrderStatusSerializer,
        responses=OrderStatusUpdateResponseSerializer,
        summary="Update order status",
        description="Tailor updates order tailor_status (accepted, in_progress, stitching_started, stitched). You can also use /accept/ endpoint to accept orders.",
        tags=["Tailor Orders"]
    )
    def patch(self, request, order_id):
        if request.user.role != 'TAILOR':
            return api_response(
                success=False,
                message="Only tailors can access this endpoint",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        order = get_object_or_404(Order, id=order_id)
        
        # Verify tailor has access
        if order.tailor != request.user:
            return api_response(
                success=False,
                message="You don't have access to this order",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        serializer = TailorUpdateOrderStatusSerializer(data=request.data)
        if serializer.is_valid():
            new_tailor_status = serializer.validated_data.get('tailor_status')
            new_status = serializer.validated_data.get('status')
            notes = serializer.validated_data.get('notes', '')
            
            # Special handling: if tailor_status is "ready_for_delivery", map it to main status
            # This allows consistent use of tailor_status field
            if new_tailor_status == 'ready_for_delivery':
                new_status = 'ready_for_delivery'
                new_tailor_status = None  # Don't update tailor_status
            
            # Store old tailor_status for notification
            old_tailor_status = order.tailor_status
            
            # Use transition service
            from apps.orders.services import OrderStatusTransitionService
            
            success, error_msg, updated_order = OrderStatusTransitionService.transition(
                order=order,
                new_status=new_status,
                new_tailor_status=new_tailor_status,
                user_role='TAILOR',
                user=request.user,
                notes=notes
            )
            
            if not success:
                return api_response(
                    success=False,
                    message=error_msg,
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            order = updated_order
            
            # Send push notification for tailor_status change if it changed
            if new_tailor_status and new_tailor_status != old_tailor_status:
                try:
                    from apps.notifications.services import NotificationService
                    NotificationService.send_tailor_status_notification(
                        order=order,
                        old_tailor_status=old_tailor_status,
                        new_tailor_status=new_tailor_status,
                        changed_by=request.user
                    )
                except Exception as e:
                    # Log error but don't fail the update
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Failed to send tailor status notification: {str(e)}")
            
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
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        request=TailorAddMeasurementsSerializer,
        responses={200: OrderSerializer},
        summary="Add measurements",
        description="Tailor adds measurements taken at the shop. Required before stitching can start.",
        tags=["Tailor Orders"]
    )
    def post(self, request, order_id):
        if request.user.role != 'TAILOR':
            return api_response(
                success=False,
                message="Only tailors can access this endpoint",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        order = get_object_or_404(
            Order.objects.select_related('family_member', 'customer'),
            id=order_id
        )
        
        # Verify tailor has access
        if order.tailor != request.user:
            return api_response(
                success=False,
                message="You don't have access to this order",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        # Verify order type
        if order.order_type != 'fabric_with_stitching':
            return api_response(
                success=False,
                message="Measurements can only be added for fabric_with_stitching orders",
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
            
            # Build message
            message = f"Measurements saved for {recipient_name}."
            if all_measured:
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
