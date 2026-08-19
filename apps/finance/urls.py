from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TailorWalletView, TailorTransactionHistoryView,
    PayoutRequestViewSet, ShopSalesSummaryView,
)

router = DefaultRouter()
router.register(r'payouts', PayoutRequestViewSet, basename='tailor-payouts')

urlpatterns = [
    path('wallet/', TailorWalletView.as_view(), name='tailor-wallet'),
    path('transactions/', TailorTransactionHistoryView.as_view(), name='tailor-transactions'),
    path('shop-sales/summary/', ShopSalesSummaryView.as_view(), name='shop-sales-summary'),
    path('', include(router.urls)),
]
