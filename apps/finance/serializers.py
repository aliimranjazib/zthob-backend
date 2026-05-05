from rest_framework import serializers
from .models import TailorWallet, WalletTransaction, PayoutRequest
from apps.orders.models import Order

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

class TailorWalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = TailorWallet
        fields = [
            'available_balance', 'pending_balance', 
            'total_earned', 'total_withdrawn'
        ]

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
        """Ensure the tailor has enough balance for the payout."""
        user = self.context['request'].user
        wallet = TailorWallet.objects.filter(tailor=user).first()
        if not wallet or wallet.available_balance < value:
            raise serializers.ValidationError("Insufficient balance for this payout request.")
        return value
