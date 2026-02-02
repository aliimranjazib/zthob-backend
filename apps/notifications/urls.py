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
]
