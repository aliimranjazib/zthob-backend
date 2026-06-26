from rest_framework import serializers
from decimal import Decimal
from django.db.models import Sum
from .models import (
    TailorWallet, WalletTransaction, PayoutRequest,
    RiderWallet, RiderWalletTransaction, RiderPayoutRequest,
)
from apps.orders.models import Order


PAYOUT_RESERVED_STATUSES = ['pending', 'approved']


def get_finance_role(user):
    if getattr(user, 'role', None) == 'RIDER':
        return 'rider'
    if getattr(user, 'role', None) == 'TAILOR':
        return 'tailor'
    if user.is_rider and not user.is_tailor:
        return 'rider'
    if user.is_tailor:
        return 'tailor'
    if user.is_rider:
        return 'rider'
    return None


def _money(value):
    return f"{(value or Decimal('0.00')).quantize(Decimal('0.01')):.2f}"


def _reserved_payout_amount(user):
    finance_role = get_finance_role(user)
    if finance_role == 'tailor':
        queryset = PayoutRequest.objects.filter(tailor=user, status__in=PAYOUT_RESERVED_STATUSES)
    elif finance_role == 'rider':
        queryset = RiderPayoutRequest.objects.filter(rider=user, status__in=PAYOUT_RESERVED_STATUSES)
    else:
        return Decimal('0.00')

    return queryset.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')


def _spendable_balance(wallet, user):
    reserved_amount = _reserved_payout_amount(user)
    spendable = wallet.available_balance - reserved_amount
    return max(spendable, Decimal('0.00'))

class OrderSummarySerializer(serializers.ModelSerializer):
    """Simplified order info for transaction history to avoid heavy nesting."""
    class Meta:
        model = Order
        fields = ['id', 'order_number', 'status', 'total_amount']

class WalletTransactionSerializer(serializers.ModelSerializer):
    order = OrderSummarySerializer(read_only=True)
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    source_display = serializers.CharField(source='get_source_display', read_only=True)

    class Meta:
        model = WalletTransaction
        fields = [
            'id', 'transaction_type', 'transaction_type_display', 
            'source', 'source_display', 'amount', 'running_balance',
            'description', 'created_at', 'order'
        ]

class RiderWalletTransactionSerializer(serializers.ModelSerializer):
    order = OrderSummarySerializer(read_only=True)
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    source_display = serializers.CharField(source='get_source_display', read_only=True)
    earning_type_display = serializers.CharField(source='get_earning_type_display', read_only=True)

    class Meta:
        model = RiderWalletTransaction
        fields = [
            'id', 'transaction_type', 'transaction_type_display',
            'source', 'source_display', 'earning_type', 'earning_type_display',
            'amount', 'running_balance',
            'description', 'created_at', 'order'
        ]

class TailorWalletSerializer(serializers.ModelSerializer):
    available_balance = serializers.SerializerMethodField()
    pending_payout_amount = serializers.SerializerMethodField()
    ledger_balance = serializers.SerializerMethodField()

    class Meta:
        model = TailorWallet
        fields = [
            'available_balance', 'pending_balance',
            'pending_payout_amount', 'ledger_balance',
            'total_earned', 'total_withdrawn'
        ]

    def get_available_balance(self, obj):
        return _money(_spendable_balance(obj, obj.tailor))

    def get_pending_payout_amount(self, obj):
        return _money(_reserved_payout_amount(obj.tailor))

    def get_ledger_balance(self, obj):
        return _money(obj.available_balance)

class RiderWalletSerializer(serializers.ModelSerializer):
    available_balance = serializers.SerializerMethodField()
    pending_payout_amount = serializers.SerializerMethodField()
    ledger_balance = serializers.SerializerMethodField()

    class Meta:
        model = RiderWallet
        fields = [
            'available_balance', 'pending_balance',
            'pending_payout_amount', 'ledger_balance',
            'total_earned', 'total_withdrawn'
        ]

    def get_available_balance(self, obj):
        return _money(_spendable_balance(obj, obj.rider))

    def get_pending_payout_amount(self, obj):
        return _money(_reserved_payout_amount(obj.rider))

    def get_ledger_balance(self, obj):
        return _money(obj.available_balance)

class PayoutRequestSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = PayoutRequest
        fields = [
            'id', 'amount', 'status', 'status_display', 
            'bank_name', 'account_number', 'iban', 'account_holder_name',
            'payment_reference', 'admin_notes', 'created_at', 'processed_at'
        ]
        read_only_fields = ['status', 'payment_reference', 'admin_notes', 'processed_at']

    def validate_amount(self, value):
        """Ensure the authenticated tailor/rider has enough balance for the payout."""
        user = self.context['request'].user
        finance_role = get_finance_role(user)
        if finance_role == 'tailor':
            wallet = TailorWallet.objects.filter(tailor=user).first()
        elif finance_role == 'rider':
            wallet = RiderWallet.objects.filter(rider=user).first()
        else:
            wallet = None
        if not wallet or _spendable_balance(wallet, user) < value:
            raise serializers.ValidationError("Insufficient balance for this payout request.")
        return value


class RiderPayoutRequestSerializer(PayoutRequestSerializer):
    class Meta(PayoutRequestSerializer.Meta):
        model = RiderPayoutRequest
