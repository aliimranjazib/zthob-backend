# apps/tailors/serializers/address.py
from rest_framework import serializers
from apps.customers.models import Address

class TailorAddressSerializer(serializers.ModelSerializer):
    """Serializer for tailor addresses."""
    
    class Meta:
        model = Address
        fields = [
            'id', 'street', 'city', 'state_province', 'zip_code', 
            'country', 'latitude', 'longitude', 'is_default', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        """Create a new address for the tailor."""
        user = self.context.get('request').user
        validated_data['user'] = user
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        """Update the address."""
        # Remove user from validated_data if it exists
        validated_data.pop('user', None)
        return super().update(instance, validated_data)

class TailorAddressCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating tailor addresses."""
    
    class Meta:
        model = Address
        fields = [
            'street', 'city', 'state_province', 'zip_code', 
            'country', 'latitude', 'longitude', 'is_default'
        ]
    
    def create(self, validated_data):
        """Create a new address for the tailor."""
        user = self.context.get('request').user
        validated_data['user'] = user
        return super().create(validated_data)

class TailorAddressUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating tailor addresses."""
    
    class Meta:
        model = Address
        fields = [
            'street', 'city', 'state_province', 'zip_code', 
            'country', 'latitude', 'longitude', 'is_default'
        ]
