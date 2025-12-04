from django.urls import path
from .views import (
    RiderUpdateLocationView,
    RiderTrackingView,
    CustomerTrackingView,
    CustomerTrackingHistoryView,
    AdminTrackingView,
    AdminTrackingRouteView,
)

app_name = 'deliveries'

urlpatterns = [
    # Rider endpoints
    path('rider/orders/<int:order_id>/update-location/', RiderUpdateLocationView.as_view(), name='rider-update-location'),
    path('rider/orders/<int:order_id>/tracking/', RiderTrackingView.as_view(), name='rider-tracking'),
    
    # Customer endpoints
    path('customer/orders/<int:order_id>/tracking/', CustomerTrackingView.as_view(), name='customer-tracking'),
    path('customer/orders/<int:order_id>/tracking/history/', CustomerTrackingHistoryView.as_view(), name='customer-tracking-history'),
    
    # Admin/Tailor endpoints
    path('admin/orders/<int:order_id>/tracking/', AdminTrackingView.as_view(), name='admin-tracking'),
    path('admin/orders/<int:order_id>/tracking/route/', AdminTrackingRouteView.as_view(), name='admin-tracking-route'),
]

