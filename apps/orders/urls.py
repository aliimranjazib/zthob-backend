from django.urls import path
from .views import (
    OrderListView,
    OrderCreateView,
    OrderDetailView,
    OrderStatusUpdateView,
    OrderHistoryView,
    CustomerOrderListView,
    TailorOrderListView,
    TailorOrderHistoryView,
    TailorAvailableOrdersView,
    TailorPaidOrdersView,
    TailorOrderDetailView,
    OrderPaymentStatusUpdateView,
    OrderMeasurementsDetailView,
    WorkOrderPDFView,
    OrderActionView,
    PayRemainingBalanceView,
    CheckoutCreateView,
    CheckoutStatusView,
    CheckoutCreateOrderView,
    CheckoutInitiatePaymentView,
    CheckoutAlinmaCallbackView,
    RemainingBalanceInitiatePaymentView,
    RemainingPaymentStatusView,
    StyleReferenceUploadView,
)
from .measurement_views import MeasurementEligibilityView
from .myfatoorah_views import (
    MyFatoorahCheckoutConfirmView,
    MyFatoorahCheckoutPrepareView,
    MyFatoorahRemainingConfirmView,
    MyFatoorahRemainingPrepareView,
    MyFatoorahWebhookView,
)

app_name = 'orders'

urlpatterns = [
    # General order endpoints
    path('', OrderListView.as_view(), name='order-list'),
    path('checkout/', CheckoutCreateView.as_view(), name='checkout-create'),
    path('checkout/initiate-payment/', CheckoutInitiatePaymentView.as_view(), name='checkout-initiate-payment'),
    path('checkout/alinma/callback/', CheckoutAlinmaCallbackView.as_view(), name='checkout-alinma-callback'),
    path('checkout/myfatoorah/prepare/', MyFatoorahCheckoutPrepareView.as_view(), name='checkout-myfatoorah-prepare'),
    path('checkout/myfatoorah/confirm/', MyFatoorahCheckoutConfirmView.as_view(), name='checkout-myfatoorah-confirm'),
    path('checkout/myfatoorah/webhook/', MyFatoorahWebhookView.as_view(), name='checkout-myfatoorah-webhook'),
    path('checkout/create-order/', CheckoutCreateOrderView.as_view(), name='checkout-create-order'),
    path('checkout/<str:booking_unique_key>/', CheckoutStatusView.as_view(), name='checkout-status'),
    path('create/', OrderCreateView.as_view(), name='order-create'),
    path('style-reference/upload/', StyleReferenceUploadView.as_view(), name='style-reference-upload'),
    path('<int:order_id>/', OrderDetailView.as_view(), name='order-detail'),
    path('<int:order_id>/status/', OrderStatusUpdateView.as_view(), name='order-status-update'),
    path('<int:order_id>/history/', OrderHistoryView.as_view(), name='order-history'),
    path('<int:order_id>/payment-status/', OrderPaymentStatusUpdateView.as_view(), name='order-payment-status-update'),
    path('<int:order_id>/pay-remaining/', PayRemainingBalanceView.as_view(), name='order-pay-remaining'),
    path('<int:order_id>/pay-remaining/initiate-payment/', RemainingBalanceInitiatePaymentView.as_view(), name='order-pay-remaining-initiate'),
    path('<int:order_id>/pay-remaining/myfatoorah/prepare/', MyFatoorahRemainingPrepareView.as_view(), name='order-pay-remaining-myfatoorah-prepare'),
    path('<int:order_id>/pay-remaining/myfatoorah/confirm/', MyFatoorahRemainingConfirmView.as_view(), name='order-pay-remaining-myfatoorah-confirm'),
    path('pay-remaining/<str:booking_unique_key>/', RemainingPaymentStatusView.as_view(), name='order-pay-remaining-status'),
    path('<int:order_id>/measurements/', OrderMeasurementsDetailView.as_view(), name='order-measurements'),
    path('<int:order_id>/action/', OrderActionView.as_view(), name='order-action'),
    
    # Measurement service endpoints
    path('measurement-eligibility/', MeasurementEligibilityView.as_view(), name='measurement-eligibility'),
    
    # Customer endpoints
    path('customer/my-orders/', CustomerOrderListView.as_view(), name='customer-orders'),
    
    # Tailor endpoints
    path('tailor/available-orders/', TailorAvailableOrdersView.as_view(), name='tailor-available-orders'),
    path('tailor/my-orders/', TailorOrderListView.as_view(), name='tailor-orders'),
    path('tailor/history/', TailorOrderHistoryView.as_view(), name='tailor-order-history'),
    path('tailor/paid-orders/', TailorPaidOrdersView.as_view(), name='tailor-paid-orders'),
    path('tailor/<int:order_id>/', TailorOrderDetailView.as_view(), name='tailor-order-detail'),
    
    # PDF endpoints
    path('<int:order_id>/work-order-pdf/', WorkOrderPDFView.as_view(), name='work-order-pdf'),
]
