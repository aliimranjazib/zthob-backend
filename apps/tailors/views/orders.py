# apps/tailors/views/orders.py
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema

from apps.orders.models import Order
from apps.tailors.serializers.orders import TailorUpdateOrderStatusSerializer
from apps.orders.serializers import OrderStatusUpdateResponseSerializer
from zthob.utils import api_response


class TailorUpdateOrderStatusView(APIView):
    """Tailor updates order status"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        request=TailorUpdateOrderStatusSerializer,
        responses=OrderStatusUpdateResponseSerializer,
        summary="Update order status",
        description="Tailor updates order tailor_status (accepted, stitching_started, stitched)",
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
            
            # Send push notification for order status change
            try:
                from apps.notifications.services import NotificationService
                NotificationService.send_order_status_notification(
                    order=order,
                    old_status=order.status,  # History will have the old status
                    new_status=order.status,
                    changed_by=request.user
                )
            except Exception as e:
                # Log error but don't fail the update
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to send order status notification: {str(e)}")
            
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

