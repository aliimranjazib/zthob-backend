from django.urls import path
from .views import (
    RegisterFCMTokenView,
    UnregisterFCMTokenView,
    NotificationLogListView,
    MarkNotificationReadView,
    MarkAllNotificationsReadView,
    UnreadCountView,
    TestNotificationView,
)

app_name = 'notifications'

urlpatterns = [
    path('fcm-token/register/', RegisterFCMTokenView.as_view(), name='register-fcm-token'),
    path('fcm-token/update/', RegisterFCMTokenView.as_view(), name='update-fcm-token'),
    path('fcm-token/unregister/', UnregisterFCMTokenView.as_view(), name='unregister-fcm-token'),
    path('logs/', NotificationLogListView.as_view(), name='notification-logs'),
    path('<int:notification_id>/read/', MarkNotificationReadView.as_view(), name='mark-notification-read'),
    path('mark-all-read/', MarkAllNotificationsReadView.as_view(), name='mark-all-read'),
    path('unread-count/', UnreadCountView.as_view(), name='unread-count'),
    path('test/', TestNotificationView.as_view(), name='test-notification'),
]

