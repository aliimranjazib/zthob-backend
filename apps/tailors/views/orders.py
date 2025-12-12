# apps/tailors/views/orders.py
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema

from apps.orders.models import Order
from apps.tailors.serializers.orders import TailorUpdateOrderStatusSerializer
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
        description="Tailor updates order tailor_status (stitching_started, stitched). Use /accept/ endpoint to accept orders.",
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
            new_tailor_status = serializer.validated_data['tailor_status']
            notes = serializer.validated_data.get('notes', '')
            
            # Don't allow accepting via this endpoint - use /accept/ instead
            if new_tailor_status == 'accepted':
                return api_response(
                    success=False,
                    message="Please use /api/tailors/orders/{order_id}/accept/ endpoint to accept orders",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Store old tailor_status for notification
            old_tailor_status = order.tailor_status
            
            # Use transition service
            from apps.orders.services import OrderStatusTransitionService
            
            success, error_msg, updated_order = OrderStatusTransitionService.transition(
                order=order,
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
            
            # Send push notification for tailor_status change
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
            return api_response(
                success=True,
                message=f"Order tailor status updated to {order.get_tailor_status_display()}",
                data=response_serializer.data,
                status_code=status.HTTP_200_OK
            )
        
        return api_response(
            success=False,
            message="Failed to update order status",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )
