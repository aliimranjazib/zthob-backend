from django.urls import path
from .views import (
    RegisterFCMTokenView,
    UnregisterFCMTokenView,
    NotificationLogListView,
)

app_name = 'notifications'

urlpatterns = [
    path('fcm-token/register/', RegisterFCMTokenView.as_view(), name='register-fcm-token'),
    path('fcm-token/update/', RegisterFCMTokenView.as_view(), name='update-fcm-token'),
    path('fcm-token/unregister/', UnregisterFCMTokenView.as_view(), name='unregister-fcm-token'),
    path('logs/', NotificationLogListView.as_view(), name='notification-logs'),
]

