from django.db.models import Q
from rest_framework import viewsets, generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied, ValidationError
from .models import (
    TailorWallet, WalletTransaction, PayoutRequest,
    RiderWallet, RiderWalletTransaction, RiderPayoutRequest,
)
from .serializers import (
    TailorWalletSerializer, WalletTransactionSerializer, 
    PayoutRequestSerializer, RiderWalletSerializer,
    RiderWalletTransactionSerializer, RiderPayoutRequestSerializer,
    ShopSalesSummarySerializer,
    get_finance_role,
)
from .shop_sales import SHOP_SALES_DEFAULT_PERIOD, get_shop_sales_summary
from .shop_session import finance_shop_required_message, resolve_finance_shop
from apps.tailors.shop_access import get_shop_owner_user
from apps.finance.services import WalletService

class TailorWalletView(APIView):
    """
    Returns the current wallet balance and summary for the authenticated tailor or rider.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        finance_role = get_finance_role(request.user)
        if finance_role == 'tailor':
            shop, shop_id = resolve_finance_shop(request)
            if not shop_id:
                return Response(
                    {'error': finance_shop_required_message()},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            owner = get_shop_owner_user(request.user, shop_id=shop_id) or request.user
            wallet = WalletService.get_or_create_shop_wallet(owner, shop)
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
            shop, shop_id = resolve_finance_shop(self.request)
            if not shop_id:
                return WalletTransaction.objects.none()
            owner = get_shop_owner_user(self.request.user, shop_id=shop_id) or self.request.user
            wallet = WalletService.get_or_create_shop_wallet(owner, shop)
            return WalletTransaction.objects.filter(wallet=wallet).filter(
                Q(order__isnull=True) | ~Q(order__service_mode='walk_in')
            ).select_related('order').order_by('-created_at')
        
        if finance_role == 'rider':
            return RiderWalletTransaction.objects.filter(
                wallet__rider=self.request.user
            ).select_related('order').order_by('-created_at')

        return WalletTransaction.objects.none()


class ShopSalesSummaryView(APIView):
    """
    Walk-in shop cash collected by the tailor for a selected period.
    Excludes platform wallet payouts (home delivery).
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if get_finance_role(request.user) != 'tailor':
            return Response(
                {"error": "Only tailors can access shop sales summary."},
                status=status.HTTP_403_FORBIDDEN,
            )

        period = request.query_params.get('period', SHOP_SALES_DEFAULT_PERIOD)
        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')

        shop, shop_id = resolve_finance_shop(request)
        if not shop_id:
            return Response(
                {'error': finance_shop_required_message()},
                status=status.HTTP_400_BAD_REQUEST,
            )
        owner = get_shop_owner_user(request.user, shop_id=shop_id) or request.user
        try:
            summary = get_shop_sales_summary(
                owner,
                period=period,
                from_date=from_date,
                to_date=to_date,
                shop_id=shop_id,
            )
        except ValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)

        serializer = ShopSalesSummarySerializer(summary)
        return Response(serializer.data)


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
            qs = PayoutRequest.objects.filter(tailor=self.request.user)
            shop, shop_id = resolve_finance_shop(self.request)
            if shop_id is not None:
                qs = qs.filter(shop_id=shop_id)
            return qs
        if finance_role == 'rider':
            return RiderPayoutRequest.objects.filter(rider=self.request.user)
        return PayoutRequest.objects.none()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if get_finance_role(self.request.user) == 'tailor':
            shop, shop_id = resolve_finance_shop(self.request)
            if shop_id:
                owner = get_shop_owner_user(self.request.user, shop_id=shop_id) or self.request.user
                context['tailor_wallet'] = WalletService.get_or_create_shop_wallet(owner, shop)
                context['shop_id'] = shop_id
                context['finance_shop'] = shop
        return context

    def perform_create(self, serializer):
        finance_role = get_finance_role(self.request.user)
        if finance_role == 'tailor':
            shop, shop_id = resolve_finance_shop(self.request)
            if not shop_id:
                raise ValidationError({'detail': finance_shop_required_message()})
            owner = get_shop_owner_user(self.request.user, shop_id=shop_id) or self.request.user
            serializer.save(tailor=owner, shop=shop)
        elif finance_role == 'rider':
            serializer.save(rider=self.request.user)
        else:
            raise PermissionDenied("Only tailors or riders can request payouts.")
