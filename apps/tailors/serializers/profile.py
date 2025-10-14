# apps/tailors/serializers/profile.py
from rest_framework import serializers
from apps.accounts.serializers import UserProfileSerializer
from apps.customers.models import Address
from ..models import TailorProfile

class AddressSerializer(serializers.ModelSerializer):
    """Serializer for address fields."""
    class Meta:
        model = Address
        fields = ['street', 'city', 'state_province', 'zip_code', 'country', 'latitude', 'longitude']
        read_only_fields = ['user']

class TailorProfileSerializer(serializers.ModelSerializer):
    user = UserProfileSerializer(read_only=True)
    shop_image_url = serializers.SerializerMethodField()
    
    # Address fields (structured like customer side)
    street = serializers.CharField(max_length=255, required=False, allow_blank=True)
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    state_province = serializers.CharField(max_length=100, required=False, allow_blank=True)
    zip_code = serializers.CharField(max_length=20, required=False, allow_blank=True)
    country = serializers.CharField(max_length=100, default="Saudi Arabia", required=False)
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    
    # Review status fields
    review_status = serializers.SerializerMethodField()
    submitted_at = serializers.SerializerMethodField()
    reviewed_at = serializers.SerializerMethodField()
    rejection_reason = serializers.SerializerMethodField()
    service_areas = serializers.SerializerMethodField()
    phone_verified = serializers.SerializerMethodField()
    
    class Meta:
        model = TailorProfile
        fields = [
            'user', 'shop_name', 'establishment_year', 
            'tailor_experience', 'working_hours', 
            'contact_number', 'address', 'shop_status',
            'shop_image', 'shop_image_url',
            'street', 'city', 'state_province', 'zip_code', 'country', 'latitude', 'longitude',
            'review_status', 'submitted_at', 'reviewed_at', 
            'rejection_reason', 'service_areas',
            'phone_verified', 
        ]
    
    def get_shop_image_url(self, obj):
        """Get the full URL of the shop image."""
        if obj.shop_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.shop_image.url)
            return obj.shop_image.url
        return None
    
    def get_review_status(self, obj):
        """Get the review status from the related review object."""
        try:
            return obj.review.review_status
        except:
            return 'draft'
    
    def get_submitted_at(self, obj):
        """Get the submission date from the related review object."""
        try:
            return obj.review.submitted_at
        except:
            return None
    
    def get_reviewed_at(self, obj):
        """Get the review date from the related review object."""
        try:
            return obj.review.reviewed_at
        except:
            return None
    
    def get_rejection_reason(self, obj):
        """Get the rejection reason from the related review object."""
        try:
            return obj.review.rejection_reason
        except:
            return None
    
    def get_service_areas(self, obj):
        """Get the service area from the related review object."""
        try:
            service_areas = obj.review.service_areas
            # Return the first service area ID as a single integer, or None if empty
            return service_areas[0] if service_areas else None
        except:
            return None
    
    def get_phone_verified(self, obj):
        """Get phone verification status from user."""
        return obj.user.phone_verified
    
    def to_representation(self, instance):
        """Override to add address fields from the legacy address field."""
        data = super().to_representation(instance)
        
        # Parse the legacy address field if it exists
        if instance.address:
            # Try to parse the address string into components
            # This is a simple implementation - you might want to improve this
            address_parts = instance.address.split(', ')
            if len(address_parts) >= 2:
                data['street'] = address_parts[0] if len(address_parts) > 0 else ''
                data['city'] = address_parts[1] if len(address_parts) > 1 else ''
                data['state_province'] = address_parts[2] if len(address_parts) > 2 else ''
                data['zip_code'] = address_parts[3] if len(address_parts) > 3 else ''
                data['country'] = address_parts[4] if len(address_parts) > 4 else 'Saudi Arabia'
        
        return data
    
    def to_internal_value(self, data):
        """Override to handle address fields and create legacy address field."""
        # Extract address fields
        address_fields = {}
        for field in ['street', 'city', 'state_province', 'zip_code', 'country']:
            if field in data:
                address_fields[field] = data.pop(field, '')
        
        # Create legacy address string
        if any(address_fields.values()):
            address_parts = []
            if address_fields.get('street'):
                address_parts.append(address_fields['street'])
            if address_fields.get('city'):
                address_parts.append(address_fields['city'])
            if address_fields.get('state_province'):
                address_parts.append(address_fields['state_province'])
            if address_fields.get('zip_code'):
                address_parts.append(address_fields['zip_code'])
            if address_fields.get('country'):
                address_parts.append(address_fields['country'])
            
            data['address'] = ', '.join(address_parts)
        
        return super().to_internal_value(data)

class TailorProfileUpdateSerializer(serializers.ModelSerializer):
    # Address fields (structured like customer side)
    street = serializers.CharField(max_length=255, required=False, allow_blank=True)
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    state_province = serializers.CharField(max_length=100, required=False, allow_blank=True)
    zip_code = serializers.CharField(max_length=20, required=False, allow_blank=True)
    country = serializers.CharField(max_length=100, default="Saudi Arabia", required=False)
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    
    class Meta:
        model = TailorProfile
        fields = [
            'shop_name', 'establishment_year', 'tailor_experience', 
            'working_hours', 'contact_number', 'address', 'shop_status',
            'shop_image', 'street', 'city', 'state_province', 'zip_code', 'country', 'latitude', 'longitude'
        ]
    
    def to_internal_value(self, data):
        """Override to handle address fields and create legacy address field."""
        # Extract address fields
        address_fields = {}
        for field in ['street', 'city', 'state_province', 'zip_code', 'country']:
            if field in data:
                address_fields[field] = data.pop(field, '')
        
        # Create legacy address string
        if any(address_fields.values()):
            address_parts = []
            if address_fields.get('street'):
                address_parts.append(address_fields['street'])
            if address_fields.get('city'):
                address_parts.append(address_fields['city'])
            if address_fields.get('state_province'):
                address_parts.append(address_fields['state_province'])
            if address_fields.get('zip_code'):
                address_parts.append(address_fields['zip_code'])
            if address_fields.get('country'):
                address_parts.append(address_fields['country'])
            
            data['address'] = ', '.join(address_parts)
        
        return super().to_internal_value(data)

class TailorProfileSubmissionSerializer(serializers.ModelSerializer):
    """Serializer for tailor profile submission for review."""
    service_areas = serializers.IntegerField(
        required=True,
        help_text="Service area ID that the tailor serves",
        write_only=True  # This field is only for input, not output
    )
    
    # Address fields (structured like customer side)
    street = serializers.CharField(max_length=255, required=False, allow_blank=True)
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    state_province = serializers.CharField(max_length=100, required=False, allow_blank=True)
    zip_code = serializers.CharField(max_length=20, required=False, allow_blank=True)
    country = serializers.CharField(max_length=100, default="Saudi Arabia", required=False)
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    
    class Meta:
        model = TailorProfile
        fields = [
            'shop_name', 'contact_number', 'establishment_year',
            'tailor_experience', 'working_hours', 'address', 'shop_image', 'service_areas',
            'street', 'city', 'state_province', 'zip_code', 'country', 'latitude', 'longitude'
        ]
    
    def to_internal_value(self, data):
        """Override to handle address fields and create legacy address field."""
        # Extract address fields
        address_fields = {}
        for field in ['street', 'city', 'state_province', 'zip_code', 'country']:
            if field in data:
                address_fields[field] = data.pop(field, '')
        
        # Create legacy address string
        if any(address_fields.values()):
            address_parts = []
            if address_fields.get('street'):
                address_parts.append(address_fields['street'])
            if address_fields.get('city'):
                address_parts.append(address_fields['city'])
            if address_fields.get('state_province'):
                address_parts.append(address_fields['state_province'])
            if address_fields.get('zip_code'):
                address_parts.append(address_fields['zip_code'])
            if address_fields.get('country'):
                address_parts.append(address_fields['country'])
            
            data['address'] = ', '.join(address_parts)
        
        return super().to_internal_value(data)
    
    def validate_service_areas(self, value):
        """Validate that the service area ID exists and is active."""
        from ..models import ServiceArea
        
        if not value:
            raise serializers.ValidationError("Service area is required.")
        
        # Check if the service area exists and is active
        try:
            service_area = ServiceArea.objects.get(id=value, is_active=True)
        except ServiceArea.DoesNotExist:
            raise serializers.ValidationError(f"Invalid or inactive service area ID: {value}")
        
        return value
    
    def validate(self, data):
        # Ensure all required fields are present for submission
        required_fields = ['shop_name', 'contact_number', 'address', 'service_areas']
        for field in required_fields:
            if not data.get(field):
                raise serializers.ValidationError(f"{field} is required for submission")
        
        # Check if shop_image is provided (either in data or already exists on instance)
        if not data.get('shop_image') and not (hasattr(self, 'instance') and self.instance and self.instance.shop_image):
            raise serializers.ValidationError("shop_image is required for submission")
        
        return data
