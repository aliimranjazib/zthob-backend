from rest_framework import viewsets, generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied
from .models import (
    TailorWallet, WalletTransaction, PayoutRequest,
    RiderWallet, RiderWalletTransaction, RiderPayoutRequest,
)
from .serializers import (
    TailorWalletSerializer, WalletTransactionSerializer, 
    PayoutRequestSerializer, RiderWalletSerializer,
    RiderWalletTransactionSerializer, RiderPayoutRequestSerializer,
    get_finance_role,
)

class TailorWalletView(APIView):
    """
    Returns the current wallet balance and summary for the authenticated tailor or rider.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        finance_role = get_finance_role(request.user)
        if finance_role == 'tailor':
            wallet, _ = TailorWallet.objects.get_or_create(tailor=request.user)
            serializer = TailorWalletSerializer(wallet)
            return Response(serializer.data)
        
        if finance_role == 'rider':
            wallet, _ = RiderWallet.objects.get_or_create(rider=request.user)
            serializer = RiderWalletSerializer(wallet)
            return Response(serializer.data)

        return Response({"error": "Only tailors or riders can access wallet info."}, status=status.HTTP_403_FORBIDDEN)


class TailorTransactionHistoryView(generics.ListAPIView):
    """
    Returns a paginated list of financial transactions for the authenticated tailor or rider.
    Uses select_related to avoid N+1 problem with associated orders.
    """
    serializer_class = WalletTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if get_finance_role(self.request.user) == 'rider':
            return RiderWalletTransactionSerializer
        return WalletTransactionSerializer

    def get_queryset(self):
        finance_role = get_finance_role(self.request.user)
        if finance_role == 'tailor':
            return WalletTransaction.objects.filter(
                wallet__tailor=self.request.user
            ).select_related('order').order_by('-created_at')
        
        if finance_role == 'rider':
            return RiderWalletTransaction.objects.filter(
                wallet__rider=self.request.user
            ).select_related('order').order_by('-created_at')

        return WalletTransaction.objects.none()


class PayoutRequestViewSet(viewsets.ModelViewSet):
    """
    ViewSet for tailors and riders to manage their payout requests.
    """
    serializer_class = PayoutRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if get_finance_role(self.request.user) == 'rider':
            return RiderPayoutRequestSerializer
        return PayoutRequestSerializer

    def get_queryset(self):
        finance_role = get_finance_role(self.request.user)
        if finance_role == 'tailor':
            return PayoutRequest.objects.filter(tailor=self.request.user)
        if finance_role == 'rider':
            return RiderPayoutRequest.objects.filter(rider=self.request.user)
        return PayoutRequest.objects.none()

    def perform_create(self, serializer):
        finance_role = get_finance_role(self.request.user)
        if finance_role == 'tailor':
            serializer.save(tailor=self.request.user)
        elif finance_role == 'rider':
            serializer.save(rider=self.request.user)
        else:
            raise PermissionDenied("Only tailors or riders can request payouts.")
