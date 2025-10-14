# apps/tailors/serializers/address.py
from rest_framework import serializers
from apps.customers.models import Address

class TailorAddressSerializer(serializers.ModelSerializer):
    """Serializer for tailor addresses."""
    
    class Meta:
        model = Address
        fields = '__all__'
        read_only_fields = ['user']

# Use the same serializer for all operations (like customer side)
TailorAddressCreateSerializer = TailorAddressSerializer
TailorAddressUpdateSerializer = TailorAddressSerializer
