from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TailorWalletView, TailorTransactionHistoryView, 
    PayoutRequestViewSet
)

router = DefaultRouter()
router.register(r'payouts', PayoutRequestViewSet, basename='tailor-payouts')

urlpatterns = [
    path('wallet/', TailorWalletView.as_view(), name='tailor-wallet'),
    path('transactions/', TailorTransactionHistoryView.as_view(), name='tailor-transactions'),
    path('', include(router.urls)),
]
