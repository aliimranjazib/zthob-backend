from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db.models import Count, Max
from apps.customers.models import CustomerProfile

User = get_user_model()


class POSCustomerOrderStyleItemSerializer(serializers.Serializer):
    item_id = serializers.IntegerField()
    family_member_name = serializers.CharField(allow_null=True)
    custom_styles = serializers.ListField(child=serializers.DictField())


class POSCustomerOrderStyleGroupSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()
    order_number = serializers.CharField()
    order_date = serializers.DateTimeField()
    items = POSCustomerOrderStyleItemSerializer(many=True)


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
    last_order_date = serializers.DateTimeField(allow_null=True)
    measurements = serializers.JSONField(allow_null=True)
    order_styles = POSCustomerOrderStyleGroupSerializer(many=True)


class CreateCustomerSerializer(serializers.Serializer):
    """
    Validates input for creating a new customer by the tailor.
    """
    phone = serializers.CharField(max_length=15)
    name = serializers.CharField(max_length=150)

    def validate_phone(self, value):
        from apps.core.phone_format import format_phone_e164, is_valid_saudi_phone, normalize_phone_to_local

        if not is_valid_saudi_phone(value):
            raise serializers.ValidationError('Enter a valid Saudi mobile number.')
        return normalize_phone_to_local(format_phone_e164(value))


class POSFamilyMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = None
        fields = [
            'id',
            'name',
            'gender',
            'relationship',
            'measurements',
            'created_source',
            'customer_edited_at',
        ]
        read_only_fields = [
            'id',
            'measurements',
            'created_source',
            'customer_edited_at',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.customers.models import FamilyMember
        self.Meta.model = FamilyMember


class POSFamilyMemberCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    gender = serializers.CharField(max_length=10, required=False, allow_blank=True, allow_null=True)
    relationship = serializers.CharField(max_length=50, required=False, allow_blank=True, allow_null=True)


class POSFamilyMemberUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False)
    gender = serializers.CharField(max_length=10, required=False, allow_blank=True, allow_null=True)
    relationship = serializers.CharField(max_length=50, required=False, allow_blank=True, allow_null=True)
