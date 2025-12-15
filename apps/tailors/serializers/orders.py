# apps/tailors/serializers/orders.py
from rest_framework import serializers
from apps.orders.models import Order


class TailorUpdateOrderStatusSerializer(serializers.Serializer):
    """Serializer for tailor updating order status (tailor_status and/or main status)"""
    tailor_status = serializers.ChoiceField(
        choices=[choice for choice in Order.TAILOR_STATUS_CHOICES if choice[0] != 'none'] + [('ready_for_delivery', 'Ready for Delivery')],
        required=False
    )
    status = serializers.ChoiceField(
        choices=Order.ORDER_STATUS_CHOICES,
        required=False
    )
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, attrs):
        """Ensure at least one status field is provided"""
        if not attrs.get('tailor_status') and not attrs.get('status'):
            raise serializers.ValidationError("Either 'tailor_status' or 'status' must be provided")
        return attrs

