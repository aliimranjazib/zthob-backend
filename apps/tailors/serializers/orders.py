# apps/tailors/serializers/orders.py
from rest_framework import serializers
from apps.orders.models import Order


class TailorUpdateOrderStatusSerializer(serializers.Serializer):
    """Serializer for tailor updating order status (stitching_started, stitched only)"""
    tailor_status = serializers.ChoiceField(
        choices=[choice for choice in Order.TAILOR_STATUS_CHOICES if choice[0] not in ['none', 'accepted']],
        required=True
    )
    notes = serializers.CharField(required=False, allow_blank=True)

