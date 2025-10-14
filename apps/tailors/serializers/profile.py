# apps/tailors/serializers/profile.py
from rest_framework import serializers
from apps.accounts.serializers import UserProfileSerializer
from ..models import TailorProfile

class TailorProfileSerializer(serializers.ModelSerializer):
    user = UserProfileSerializer(read_only=True)
    shop_image_url = serializers.SerializerMethodField()
    
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

class TailorProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TailorProfile
        fields = [
            'shop_name', 'establishment_year', 'tailor_experience', 
            'working_hours', 'contact_number', 'address', 'shop_status',
            'shop_image'
        ]

class TailorProfileSubmissionSerializer(serializers.ModelSerializer):
    """Serializer for tailor profile submission for review."""
    service_areas = serializers.IntegerField(
        required=True,
        help_text="Service area ID that the tailor serves",
        write_only=True  # This field is only for input, not output
    )
    
    class Meta:
        model = TailorProfile
        fields = [
            'shop_name', 'contact_number', 'establishment_year',
            'tailor_experience', 'working_hours', 'address', 'shop_image', 'service_areas'
        ]
    
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
