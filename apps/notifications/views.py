from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from .models import NotificationLog
from .serializers import NotificationLogSerializer

# Base class to avoid code duplication
class BaseNotificationListView(generics.ListAPIView):
    serializer_class = NotificationLogSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # This will be overridden by subclasses or we can use a role paremeter
        return NotificationLog.objects.filter(user=self.request.user)

# 1. Customer Notifications
class CustomerNotificationListView(BaseNotificationListView):
    def get_queryset(self):
        # We might want to filter by category or just return all for this user
        # For now, simplistic approach: all notifications for this user
        return NotificationLog.objects.filter(
            user=self.request.user
        ).order_by('-created_at')

# 2. Tailor Notifications
class TailorNotificationListView(BaseNotificationListView):
    def get_queryset(self):
        # If tailors are just users, logic is same. 
        # But if you want to filter ONLY tailor-relevant notifications:
        return NotificationLog.objects.filter(
            user=self.request.user,
            # category__startswith='tailor_' # Optional: strict filtering
        ).order_by('-created_at')

# 3. Rider Notifications
class RiderNotificationListView(BaseNotificationListView):
    def get_queryset(self):
        return NotificationLog.objects.filter(
            user=self.request.user
            # category__startswith='rider_' # Optional
        ).order_by('-created_at')

# 4. Mark as Read Endpoint
class MarkNotificationReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            notification = NotificationLog.objects.get(pk=pk, user=request.user)
            if not notification.is_read:
                notification.is_read = True
                notification.read_at = timezone.now()
                notification.save()
            return Response({'status': 'marked as read'})
        except NotificationLog.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

# 5. Mark ALL as Read (Optional but standard)
class MarkAllReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        NotificationLog.objects.filter(
            user=request.user, 
            is_read=False
        ).update(is_read=True, read_at=timezone.now())
        return Response({'status': 'all marked as read'})

# 6. Test Notification Endpoints
class TestCustomerNotificationView(APIView):
    """Send a test notification to the logged-in customer"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        from .services import NotificationService
        
        # Verify user is a customer
        if request.user.role != 'CUSTOMER':
            return Response(
                {'error': 'This endpoint is only for customers'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Send test notification
        success = NotificationService.send_notification(
            user=request.user,
            title='Test Notification',
            body='This is a test notification for customers. If you received this, your notifications are working! 🎉',
            notification_type='TEST',
            category='test_notification',
            data={'test': True, 'timestamp': timezone.now().isoformat()},
            priority='high'
        )
        
        if success:
            return Response({
                'message': 'Test notification sent successfully',
                'success': True
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'message': 'Failed to send test notification. Check your FCM token.',
                'success': False
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TestTailorNotificationView(APIView):
    """Send a test notification to the logged-in tailor"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        from .services import NotificationService
        
        # Verify user is a tailor
        if request.user.role != 'TAILOR':
            return Response(
                {'error': 'This endpoint is only for tailors'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Send test notification
        success = NotificationService.send_notification(
            user=request.user,
            title='Test Notification',
            body='This is a test notification for tailors. If you received this, your notifications are working! 🎉',
            notification_type='TEST',
            category='test_notification',
            data={'test': True, 'timestamp': timezone.now().isoformat()},
            priority='high'
        )
        
        if success:
            return Response({
                'message': 'Test notification sent successfully',
                'success': True
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'message': 'Failed to send test notification. Check your FCM token.',
                'success': False
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TestRiderNotificationView(APIView):
    """Send a test notification to the logged-in rider"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        from .services import NotificationService
        
        # Verify user is a rider
        if request.user.role != 'RIDER':
            return Response(
                {'error': 'This endpoint is only for riders'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Send test notification
        success = NotificationService.send_notification(
            user=request.user,
            title='Test Notification',
            body='This is a test notification for riders. If you received this, your notifications are working! 🎉',
            notification_type='TEST',
            category='test_notification',
            data={'test': True, 'timestamp': timezone.now().isoformat()},
            priority='high'
        )
        
        if success:
            return Response({
                'message': 'Test notification sent successfully',
                'success': True
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'message': 'Failed to send test notification. Check your FCM token.',
                'success': False
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
