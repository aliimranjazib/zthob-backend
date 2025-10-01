from django.urls import path

from .views import(
    OrderListView,
    OrderCreateView,
    OrderDetailView,
    OrderStatusUpdateView,
    OrderHistoryView,
    CustomerOrderListView,
    TailorOrderListView
)

urlpatterns=[

path('',OrderListView.as_view(), name='order-list'),
path('create/',OrderCreateView.as_view(),name='order-create'),
path('<int:order_id>/',OrderDetailView.as_view(),name='order-detail'),
path('<int:order_id>/status/',OrderStatusUpdateView.as_view(),name='order-status-update'),
path('<int:order_id>/history/',OrderHistoryView.as_view(), name='order-history'),

path('my-orders/',CustomerOrderListView.as_view(),name='customer-orders'),
path('my-tailor-orders/',TailorOrderListView.as_view(),name='tailor-orders'),




]