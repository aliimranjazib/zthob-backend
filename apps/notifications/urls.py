from django.urls import path
from . import views

urlpatterns = [
    # Role-based notification lists
    path('customer/', views.CustomerNotificationListView.as_view(), name='customer-notifications'),
    path('tailor/', views.TailorNotificationListView.as_view(), name='tailor-notifications'),
    path('rider/', views.RiderNotificationListView.as_view(), name='rider-notifications'),
    
    # Read status actions
    path('<int:pk>/read/', views.MarkNotificationReadView.as_view(), name='mark-notification-read'),
    path('read-all/', views.MarkAllReadView.as_view(), name='mark-all-read'),
    
    # Test notification endpoints
    path('test-customer/', views.TestCustomerNotificationView.as_view(), name='test-customer-notification'),
    path('test-tailor/', views.TestTailorNotificationView.as_view(), name='test-tailor-notification'),
    path('test-rider/', views.TestRiderNotificationView.as_view(), name='test-rider-notification'),
]
