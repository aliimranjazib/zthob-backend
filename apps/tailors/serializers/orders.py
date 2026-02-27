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
    assigned_rider_id = serializers.IntegerField(required=False, allow_null=True)
    
    def validate(self, attrs):
        """Ensure at least one field is provided"""
        if not attrs.get('tailor_status') and not attrs.get('status') and not attrs.get('assigned_rider_id'):
            raise serializers.ValidationError("Either 'tailor_status', 'status' or 'assigned_rider_id' must be provided")
        return attrs


class TailorAddMeasurementsSerializer(serializers.Serializer):
    """Serializer for tailor adding measurements"""
    family_member = serializers.IntegerField(required=False, allow_null=True, help_text="ID of family member being measured. Null means customer.")
    title = serializers.CharField(required=False, allow_blank=True, help_text="Title for measurements (e.g. 'Wedding Thobe')")
    measurements = serializers.JSONField(required=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_measurements(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Measurements must be a dictionary/JSON object")
        if not value:
            raise serializers.ValidationError("Measurements cannot be empty")
        return value

