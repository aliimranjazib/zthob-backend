from rest_framework import viewsets, generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q
from .models import TailorWallet, WalletTransaction, PayoutRequest
from .serializers import (
    TailorWalletSerializer, WalletTransactionSerializer, 
    PayoutRequestSerializer
)

class TailorWalletView(APIView):
    """
    Returns the current wallet balance and summary for the authenticated tailor.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.role != 'TAILOR':
            return Response({"error": "Only tailors can access wallet info."}, status=status.HTTP_403_FORBIDDEN)
        
        wallet, _ = TailorWallet.objects.get_or_create(tailor=request.user)
        serializer = TailorWalletSerializer(wallet)
        return Response(serializer.data)


class TailorTransactionHistoryView(generics.ListAPIView):
    """
    Returns a paginated list of financial transactions for the authenticated tailor.
    Uses select_related to avoid N+1 problem with associated orders.
    """
    serializer_class = WalletTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role != 'TAILOR':
            return WalletTransaction.objects.none()
        
        return WalletTransaction.objects.filter(
            wallet__tailor=self.request.user
        ).select_related('order').order_by('-created_at')


class PayoutRequestViewSet(viewsets.ModelViewSet):
    """
    ViewSet for tailors to manage their payout requests.
    """
    serializer_class = PayoutRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role != 'TAILOR':
            return PayoutRequest.objects.none()
        return PayoutRequest.objects.filter(tailor=self.request.user)

    def perform_create(self, serializer):
        serializer.save(tailor=self.request.user)
