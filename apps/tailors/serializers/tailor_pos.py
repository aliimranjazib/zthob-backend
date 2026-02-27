from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db.models import Count, Max
from apps.customers.models import CustomerProfile

User = get_user_model()


class TailorCustomerSerializer(serializers.Serializer):
    """
    Serializes customer info for the tailor's POS customer list.
    Built from Order queryset aggregation, not a ModelSerializer.
    """
    id = serializers.IntegerField()
    name = serializers.CharField()
    phone = serializers.CharField()
    email = serializers.EmailField(allow_null=True)
    total_orders = serializers.IntegerField()
    last_order_date = serializers.DateTimeField()
    measurements = serializers.JSONField(allow_null=True)


class CreateCustomerSerializer(serializers.Serializer):
    """
    Validates input for creating a new customer by the tailor.
    """
    phone = serializers.CharField(max_length=15)
    name = serializers.CharField(max_length=150)

    def validate_phone(self, value):
        # Normalize: ensure it starts with +
        if not value.startswith('+'):
            value = '+' + value
        return value
