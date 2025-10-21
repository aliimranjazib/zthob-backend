# apps/tailors/serializers/address.py
from rest_framework import serializers
from apps.customers.models import Address

class TailorAddressSerializer(serializers.ModelSerializer):
    """Serializer for tailor's single address."""
    
    class Meta:
        model = Address
        fields = '__all__'
        read_only_fields = ['user']

class TailorAddressCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating tailor's single address."""
    
    class Meta:
        model = Address
        fields = ['street', 'city', 'state_province', 'zip_code', 'country', 'latitude', 'longitude', 'formatted_address', 'address_tag']
    
    def validate_address_tag(self, value):
        """Validate address_tag field"""
        valid_tags = [choice[0] for choice in Address.ADDRESS_TAG_CHOICES]
        if value not in valid_tags:
            raise serializers.ValidationError(f"Invalid address_tag. Must be one of: {', '.join(valid_tags)}")
        return value
    
    def create(self, validated_data):
        """Create a new address for the tailor, replacing any existing one."""
        user = self.context.get('request').user
        
        # Delete any existing address for this tailor
        Address.objects.filter(user=user).delete()
        
        # Create new address
        validated_data['user'] = user
        validated_data['is_default'] = True  # Since it's the only address
        return super().create(validated_data)

class TailorAddressUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating tailor's single address."""
    
    class Meta:
        model = Address
        fields = ['street', 'city', 'state_province', 'zip_code', 'country', 'latitude', 'longitude', 'formatted_address', 'address_tag']
    
    def validate_address_tag(self, value):
        """Validate address_tag field"""
        valid_tags = [choice[0] for choice in Address.ADDRESS_TAG_CHOICES]
        if value not in valid_tags:
            raise serializers.ValidationError(f"Invalid address_tag. Must be one of: {', '.join(valid_tags)}")
        return value
