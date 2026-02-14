from django.urls import path
from .views import (
    OrderListView,
    OrderCreateView,
    OrderDetailView,
    OrderStatusUpdateView,
    OrderHistoryView,
    CustomerOrderListView,
    TailorOrderListView,
    TailorAvailableOrdersView,
    TailorPaidOrdersView,
    TailorOrderDetailView,
    OrderPaymentStatusUpdateView,
    OrderMeasurementsDetailView,
    WorkOrderPDFView,
    AdminDashboardView,
)
from .measurement_views import MeasurementEligibilityView

app_name = 'orders'

urlpatterns = [
    # General order endpoints
    path('', OrderListView.as_view(), name='order-list'),
    path('create/', OrderCreateView.as_view(), name='order-create'),
    path('<int:order_id>/', OrderDetailView.as_view(), name='order-detail'),
    path('<int:order_id>/status/', OrderStatusUpdateView.as_view(), name='order-status-update'),
    path('<int:order_id>/history/', OrderHistoryView.as_view(), name='order-history'),
    path('<int:order_id>/payment-status/', OrderPaymentStatusUpdateView.as_view(), name='order-payment-status-update'),
    path('<int:order_id>/measurements/', OrderMeasurementsDetailView.as_view(), name='order-measurements'),
    
    # Measurement service endpoints
    path('measurement-eligibility/', MeasurementEligibilityView.as_view(), name='measurement-eligibility'),
    
    # Customer endpoints
    path('customer/my-orders/', CustomerOrderListView.as_view(), name='customer-orders'),
    
    # Tailor endpoints
    path('tailor/available-orders/', TailorAvailableOrdersView.as_view(), name='tailor-available-orders'),
    path('tailor/my-orders/', TailorOrderListView.as_view(), name='tailor-orders'),
    path('tailor/paid-orders/', TailorPaidOrdersView.as_view(), name='tailor-paid-orders'),
    path('tailor/<int:order_id>/', TailorOrderDetailView.as_view(), name='tailor-order-detail'),
    
    # PDF endpoints
    path('<int:order_id>/work-order-pdf/', WorkOrderPDFView.as_view(), name='work-order-pdf'),

    # Admin endpoints
    path('admin/dashboard/', AdminDashboardView.as_view(), name='admin-dashboard'),
]
