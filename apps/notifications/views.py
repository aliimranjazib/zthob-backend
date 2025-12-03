from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.core.paginator import Paginator

from zthob.utils import api_response
from .models import FCMDeviceToken, NotificationLog
from .serializers import FCMDeviceTokenSerializer, NotificationLogSerializer
from .services import NotificationService


class RegisterFCMTokenView(APIView):
    """Register or update FCM device token"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        request=FCMDeviceTokenSerializer,
        responses=FCMDeviceTokenSerializer,
        summary="Register FCM Token",
        description="Register or update Firebase Cloud Messaging device token for push notifications",
        tags=["Notifications"]
    )
    def post(self, request):
        serializer = FCMDeviceTokenSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            fcm_token = serializer.save()
            return api_response(
                success=True,
                message="FCM token registered successfully",
                data=serializer.data,
                status_code=status.HTTP_201_CREATED
            )
        
        return api_response(
            success=False,
            message="Failed to register FCM token",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    @extend_schema(
        request=FCMDeviceTokenSerializer,
        responses=FCMDeviceTokenSerializer,
        summary="Update FCM Token",
        description="Update existing FCM device token",
        tags=["Notifications"]
    )
    def put(self, request, token_id=None):
        # If token_id is provided, update specific token
        if token_id:
            fcm_token = get_object_or_404(
                FCMDeviceToken,
                id=token_id,
                user=request.user
            )
            serializer = FCMDeviceTokenSerializer(
                fcm_token,
                data=request.data,
                partial=True,
                context={'request': request}
            )
        else:
            # Update based on token value
            token = request.data.get('token')
            if not token:
                return api_response(
                    success=False,
                    message="Token is required",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            fcm_token = FCMDeviceToken.objects.filter(
                token=token,
                user=request.user
            ).first()
            
            if not fcm_token:
                return api_response(
                    success=False,
                    message="FCM token not found",
                    status_code=status.HTTP_404_NOT_FOUND
                )
            
            serializer = FCMDeviceTokenSerializer(
                fcm_token,
                data=request.data,
                partial=True,
                context={'request': request}
            )
        
        if serializer.is_valid():
            serializer.save()
            return api_response(
                success=True,
                message="FCM token updated successfully",
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )
        
        return api_response(
            success=False,
            message="Failed to update FCM token",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class UnregisterFCMTokenView(APIView):
    """Unregister (deactivate) FCM device token"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Unregister FCM Token",
        description="Deactivate FCM device token",
        tags=["Notifications"]
    )
    def post(self, request):
        token = request.data.get('token')
        device_id = request.data.get('device_id')
        
        if not token and not device_id:
            return api_response(
                success=False,
                message="Either token or device_id is required",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        if token:
            fcm_tokens = FCMDeviceToken.objects.filter(
                token=token,
                user=request.user
            )
        else:
            fcm_tokens = FCMDeviceToken.objects.filter(
                device_id=device_id,
                user=request.user
            )
        
        if not fcm_tokens.exists():
            return api_response(
                success=False,
                message="FCM token not found",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # Deactivate tokens
        count = fcm_tokens.update(is_active=False)
        
        return api_response(
            success=True,
            message=f"Successfully unregistered {count} FCM token(s)",
            status_code=status.HTTP_200_OK
        )


class NotificationLogListView(APIView):
    """Get notification logs for authenticated user with pagination and filtering"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        responses=NotificationLogSerializer(many=True),
        summary="Get Notification Logs",
        description="Retrieve notification history for the authenticated user with pagination, filtering, and unread count. Supports filtering by notification_type, category, and is_read status.",
        tags=["Notifications"]
    )
    def get(self, request):
        # Base queryset - filter by user
        queryset = NotificationLog.objects.filter(user=request.user)
        
        # Filter by notification_type
        notification_type = request.query_params.get('notification_type')
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)
        
        # Filter by category
        category = request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
        
        # Filter by is_read status
        is_read_param = request.query_params.get('is_read')
        if is_read_param is not None:
            is_read = is_read_param.lower() in ('true', '1', 'yes')
            queryset = queryset.filter(is_read=is_read)
        
        # Order by created_at descending (newest first)
        queryset = queryset.order_by('-created_at')
        
        # Calculate unread count before pagination
        unread_count = NotificationLog.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        
        # Pagination
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        
        # Limit page_size to max 100
        if page_size > 100:
            page_size = 100
        
        paginator = Paginator(queryset, page_size)
        total_count = paginator.count
        
        try:
            page_obj = paginator.page(page)
        except Exception:
            page_obj = paginator.page(1)
            page = 1
        
        serializer = NotificationLogSerializer(page_obj.object_list, many=True)
        
        # Build pagination response
        response_data = {
            'count': total_count,
            'unread_count': unread_count,
            'page': page,
            'page_size': page_size,
            'total_pages': paginator.num_pages,
            'results': serializer.data,
        }
        
        # Add next and previous page URLs if available
        if page_obj.has_next():
            response_data['next'] = f"?page={page_obj.next_page_number()}&page_size={page_size}"
        else:
            response_data['next'] = None
            
        if page_obj.has_previous():
            response_data['previous'] = f"?page={page_obj.previous_page_number()}&page_size={page_size}"
        else:
            response_data['previous'] = None
        
        return api_response(
            success=True,
            message="Notification logs retrieved successfully",
            data=response_data,
            status_code=status.HTTP_200_OK
        )


class MarkNotificationReadView(APIView):
    """Mark a single notification as read"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Mark Notification as Read",
        description="Mark a specific notification as read by the authenticated user",
        tags=["Notifications"]
    )
    def patch(self, request, notification_id):
        notification = get_object_or_404(
            NotificationLog,
            id=notification_id,
            user=request.user
        )
        
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=['is_read', 'read_at'])
        
        serializer = NotificationLogSerializer(notification)
        
        return api_response(
            success=True,
            message="Notification marked as read",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )


class MarkAllNotificationsReadView(APIView):
    """Mark all notifications as read for authenticated user"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Mark All Notifications as Read",
        description="Mark all unread notifications as read for the authenticated user",
        tags=["Notifications"]
    )
    def patch(self, request):
        # Get count before update
        unread_count = NotificationLog.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        
        # Mark all unread notifications as read
        updated_count = NotificationLog.objects.filter(
            user=request.user,
            is_read=False
        ).update(
            is_read=True,
            read_at=timezone.now()
        )
        
        return api_response(
            success=True,
            message=f"Marked {updated_count} notification(s) as read",
            data={
                'updated_count': updated_count,
                'unread_count': unread_count - updated_count
            },
            status_code=status.HTTP_200_OK
        )


class UnreadCountView(APIView):
    """Get unread notification count for authenticated user"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Get Unread Notification Count",
        description="Get the count of unread notifications for the authenticated user. Useful for badge counts.",
        tags=["Notifications"]
    )
    def get(self, request):
        unread_count = NotificationLog.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        
        return api_response(
            success=True,
            message="Unread count retrieved successfully",
            data={
                'unread_count': unread_count
            },
            status_code=status.HTTP_200_OK
        )


class TestNotificationView(APIView):
    """Send a test notification to the authenticated tailor"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Send Test Notification",
        description="Send a test push notification to the authenticated tailor. Requires FCM token to be registered first.",
        tags=["Notifications"]
    )
    def post(self, request):
        # Check if user is a tailor
        if getattr(request.user, 'role', None) != 'TAILOR':
            return api_response(
                success=False,
                message="This endpoint is only available for tailors",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        # Check if user has registered FCM token
        fcm_tokens = FCMDeviceToken.objects.filter(
            user=request.user,
            is_active=True
        )
        
        if not fcm_tokens.exists():
            return api_response(
                success=False,
                message="No active FCM token found. Please register your FCM token first using /api/notifications/fcm-token/register/",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # Send test notification
        try:
            success = NotificationService.send_notification(
                user=request.user,
                title="Test Notification",
                body=f"Hello {request.user.username}! This is a test notification from Zthob.",
                notification_type='SYSTEM',
                category='test_notification',
                data={
                    'test': 'true',
                    'timestamp': str(request.user.id)
                },
                priority='high'
            )
            
            if success:
                return api_response(
                    success=True,
                    message="Test notification sent successfully! Check your device.",
                    data={
                        'user': request.user.username,
                        'fcm_tokens_count': fcm_tokens.count()
                    },
                    status_code=status.HTTP_200_OK
                )
            else:
                return api_response(
                    success=False,
                    message="Failed to send test notification. Check notification logs for details.",
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error sending test notification: {str(e)}")
            return api_response(
                success=False,
                message=f"Error sending test notification: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RiderTestNotificationView(APIView):
    """Send a test notification to the authenticated rider"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Send Test Notification (Rider)",
        description="Send a test push notification to the authenticated rider. Requires FCM token to be registered first.",
        tags=["Notifications"]
    )
    def post(self, request):
        # Check if user is a rider
        if getattr(request.user, 'role', None) != 'RIDER':
            return api_response(
                success=False,
                message="This endpoint is only available for riders",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        # Check if user has registered FCM token
        fcm_tokens = FCMDeviceToken.objects.filter(
            user=request.user,
            is_active=True
        )
        
        if not fcm_tokens.exists():
            return api_response(
                success=False,
                message="No active FCM token found. Please register your FCM token first using /api/notifications/fcm-token/register/",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # Send test notification
        try:
            success = NotificationService.send_notification(
                user=request.user,
                title="Test Notification",
                body=f"Hello {request.user.username}! This is a test notification from Zthob.",
                notification_type='SYSTEM',
                category='test_notification',
                data={
                    'test': 'true',
                    'timestamp': str(request.user.id)
                },
                priority='high'
            )
            
            if success:
                return api_response(
                    success=True,
                    message="Test notification sent successfully! Check your device.",
                    data={
                        'user': request.user.username,
                        'fcm_tokens_count': fcm_tokens.count()
                    },
                    status_code=status.HTTP_200_OK
                )
            else:
                return api_response(
                    success=False,
                    message="Failed to send test notification. Check notification logs for details.",
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error sending test notification: {str(e)}")
            return api_response(
                success=False,
                message=f"Error sending test notification: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

