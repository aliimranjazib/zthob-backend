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
    """Simplified serializer for creating tailor's single address."""
    address = serializers.CharField(max_length=255, help_text="Full address text")
    address_tag = serializers.ChoiceField(choices=Address.ADDRESS_TAG_CHOICES, default='work', help_text="Address type: home, office, work, other")
    is_default = serializers.BooleanField(default=True, help_text="Whether this is the default address")
    
    class Meta:
        model = Address
        fields = ['latitude', 'longitude', 'address', 'extra_info', 'address_tag', 'is_default']
    
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
        
        # Map the 'address' field to 'street' field in the model
        address_text = validated_data.pop('address')
        is_default = validated_data.pop('is_default', True)
        
        # Set default values for required fields
        validated_data.update({
            'user': user,
            'street': address_text,
            'city': 'Riyadh',  # Default city, can be updated later
            'country': 'Saudi Arabia',
            'is_default': is_default,
        })
        
        return super().create(validated_data)

class TailorAddressUpdateSerializer(serializers.ModelSerializer):
    """Simplified serializer for updating tailor's single address."""
    address = serializers.CharField(max_length=255, help_text="Full address text")
    address_tag = serializers.ChoiceField(choices=Address.ADDRESS_TAG_CHOICES, help_text="Address type: home, office, work, other")
    is_default = serializers.BooleanField(help_text="Whether this is the default address")
    
    class Meta:
        model = Address
        fields = ['latitude', 'longitude', 'address', 'extra_info', 'address_tag', 'is_default']
    
    def validate_address_tag(self, value):
        """Validate address_tag field"""
        valid_tags = [choice[0] for choice in Address.ADDRESS_TAG_CHOICES]
        if value not in valid_tags:
            raise serializers.ValidationError(f"Invalid address_tag. Must be one of: {', '.join(valid_tags)}")
        return value
    
    def update(self, instance, validated_data):
        """Update the existing address."""
        # Map the 'address' field to 'street' field in the model
        address_text = validated_data.pop('address')
        
        instance.street = address_text
        instance.latitude = validated_data.get('latitude', instance.latitude)
        instance.longitude = validated_data.get('longitude', instance.longitude)
        instance.extra_info = validated_data.get('extra_info', instance.extra_info)
        instance.address_tag = validated_data.get('address_tag', instance.address_tag)
        instance.is_default = validated_data.get('is_default', instance.is_default)
        instance.save()
        
        return instance

class TailorAddressResponseSerializer(serializers.ModelSerializer):
    """Simplified response serializer for tailor addresses."""
    address = serializers.SerializerMethodField()
    
    class Meta:
        model = Address
        fields = ['id', 'latitude', 'longitude', 'address', 'extra_info', 'is_default', 'address_tag']
    
    def get_address(self, obj):
        """Return the street field as 'address' for consistency."""
        # If street is empty, try to construct from other fields
        if obj.street:
            return obj.street
        
        # Fallback: construct address from available fields
        address_parts = []
        if obj.city:
            address_parts.append(obj.city)
        if obj.state_province:
            address_parts.append(obj.state_province)
        if obj.country:
            address_parts.append(obj.country)
        
        if address_parts:
            return ', '.join(address_parts)
        
        # If no address components available, return a default message
        return 'Address not specified'
