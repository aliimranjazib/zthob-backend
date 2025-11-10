from django.urls import path
from .views import (
    OrderListView,
    OrderCreateView,
    OrderDetailView,
    OrderStatusUpdateView,
    OrderHistoryView,
    CustomerOrderListView,
    TailorOrderListView,
    TailorPaidOrdersView,
    TailorOrderDetailView,
    OrderPaymentStatusUpdateView,
)

app_name = 'orders'

urlpatterns = [
    # General order endpoints
    path('', OrderListView.as_view(), name='order-list'),
    path('create/', OrderCreateView.as_view(), name='order-create'),
    path('<int:order_id>/', OrderDetailView.as_view(), name='order-detail'),
    path('<int:order_id>/status/', OrderStatusUpdateView.as_view(), name='order-status-update'),
    path('<int:order_id>/history/', OrderHistoryView.as_view(), name='order-history'),
    path('<int:order_id>/payment-status/', OrderPaymentStatusUpdateView.as_view(), name='order-payment-status-update'),
    
    # Customer endpoints
    path('customer/my-orders/', CustomerOrderListView.as_view(), name='customer-orders'),
    
    # Tailor endpoints
    path('tailor/my-orders/', TailorOrderListView.as_view(), name='tailor-orders'),
    path('tailor/paid-orders/', TailorPaidOrdersView.as_view(), name='tailor-paid-orders'),
    path('tailor/<int:order_id>/', TailorOrderDetailView.as_view(), name='tailor-order-detail'),
]
