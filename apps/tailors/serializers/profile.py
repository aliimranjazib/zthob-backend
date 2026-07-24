# apps/tailors/serializers/profile.py
from decimal import Decimal

from rest_framework import serializers
from apps.accounts.serializers import UserProfileSerializer
from apps.customers.models import Address
from ..models import TailorProfile
from ..services.stitching_time import get_average_stitching_time_stats
from apps.core.media_utils import build_public_media_url

class TailorProfileSerializer(serializers.ModelSerializer):
    user = UserProfileSerializer(read_only=True)
    shop_image_url = serializers.SerializerMethodField()
    average_stitching_time_days = serializers.SerializerMethodField()
    completed_stitching_orders_count = serializers.SerializerMethodField()
    
    # Review status fields
    review_status = serializers.SerializerMethodField()
    submitted_at = serializers.SerializerMethodField()
    reviewed_at = serializers.SerializerMethodField()
    rejection_reason = serializers.SerializerMethodField()
    service_areas = serializers.SerializerMethodField()
    phone_verified = serializers.SerializerMethodField()
    
    # Address field - show structured address from Address model
    address = serializers.SerializerMethodField()
    
    is_express = serializers.BooleanField(source='is_express_delivery_enabled', read_only=True)
    
    class Meta:
        model = TailorProfile
        fields = [
            'user', 'shop_name', 'establishment_year', 
            'tailor_experience', 'working_hours', 
            'address', 'shop_status',
            'shop_image', 'shop_image_url',
            'review_status', 'submitted_at', 'reviewed_at', 
            'rejection_reason', 'service_areas',
            'phone_verified',
            'avg_stitching_quality', 'avg_on_time_delivery',
            'avg_overall_satisfaction', 'rating_count',
            'average_stitching_time_days', 'completed_stitching_orders_count',
            'is_express_delivery_enabled', 'is_express',
            'express_delivery_unit', 'express_delivery_days', 'express_delivery_fee',
            'measurement_fee',
        ]

    def _get_stitching_time_stats(self, obj):
        cache = self.context.setdefault('tailor_stitching_time_stats', {})
        user_id = obj.user_id
        if user_id not in cache:
            cache[user_id] = get_average_stitching_time_stats(obj.user)
        return cache[user_id]

    def get_average_stitching_time_days(self, obj):
        return self._get_stitching_time_stats(obj)['average_stitching_time_days']

    def get_completed_stitching_orders_count(self, obj):
        return self._get_stitching_time_stats(obj)['completed_stitching_orders_count']
    
    def get_shop_image_url(self, obj):
        """Get the full URL of the shop image."""
        if obj.shop_image:
            request = self.context.get('request')
            return build_public_media_url(request, obj.shop_image.url)
        return None
    
    def get_address(self, obj):
        """Get the simplified address from the Address model."""
        try:
            # Check if addresses were pre-fetched via related_name 'addresses' on user
            user_addresses = getattr(obj.user, 'addresses', None)
            
            address = None
            if user_addresses is not None and hasattr(user_addresses, 'all'):
                # Handle both pre-fetched QuerySet and direct DB call
                addresses = list(user_addresses.all())
                address = next((a for a in addresses if a.is_default), None)
                if not address and addresses:
                    address = addresses[0]
            else:
                # Fallback to single query if not pre-fetched
                address = Address.objects.filter(user=obj.user, is_default=True).first()
                if not address:
                    address = Address.objects.filter(user=obj.user).first()
            
            if address:
                return {
                    'id': address.id,
                    'latitude': address.latitude,
                    'longitude': address.longitude,
                    'address': address.address or '',
                    'extra_info': address.extra_info,
                    'is_default': address.is_default,
                    'address_tag': address.address_tag
                }
            return None
        except Exception:
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
        """Get the service area name from the related review object."""
        try:
            # Check if review is pre-fetched
            review = getattr(obj, 'review', None)
            if not review:
                return None
                
            service_areas = review.service_areas
            if service_areas and len(service_areas) > 0:
                # Get the first service area ID
                service_area_id = service_areas[0]
                
                # Use context to cache service area names to avoid N+1
                service_area_names = self.context.get('service_area_names')
                if service_area_names and service_area_id in service_area_names:
                    return service_area_names[service_area_id]
                
                # Fetch the service area object to get name (fallback)
                from ..models import ServiceArea
                try:
                    service_area = ServiceArea.objects.get(id=service_area_id)
                    return service_area.name
                except ServiceArea.DoesNotExist:
                    return None
            return None
        except Exception:
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
            'shop_image', 'is_express_delivery_enabled',
            'express_delivery_unit', 'express_delivery_days', 'express_delivery_fee',
        ]

    def validate(self, attrs):
        enabled = attrs.get(
            'is_express_delivery_enabled',
            getattr(self.instance, 'is_express_delivery_enabled', False) if self.instance else False,
        )
        unit = attrs.get(
            'express_delivery_unit',
            getattr(self.instance, 'express_delivery_unit', 'days') if self.instance else 'days',
        )
        value = attrs.get(
            'express_delivery_days',
            getattr(self.instance, 'express_delivery_days', None) if self.instance else None,
        )

        if not enabled:
            return attrs

        if value is None:
            raise serializers.ValidationError({
                'express_delivery_days': 'Express duration is required when express delivery is enabled.'
            })

        from apps.core.express_delivery import is_allowed_express_selection
        if not is_allowed_express_selection(value, unit):
            raise serializers.ValidationError({
                'express_delivery_days': (
                    'Selected express duration is not allowed. '
                    'Choose an option from GET /api/tailors/config/ express_delivery_options.'
                )
            })
        return attrs

class TailorMeasurementFeeSerializer(serializers.ModelSerializer):
    measurement_fee = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal('0.00'),
    )

    class Meta:
        model = TailorProfile
        fields = ['measurement_fee']

class TailorProfileSubmissionSerializer(serializers.ModelSerializer):
    """Serializer for tailor profile submission for review."""
    service_areas = serializers.IntegerField(
        required=True,
        help_text="Service area ID that the tailor serves",
        write_only=True  # This field is only for input, not output
    )
    contact_number = serializers.CharField(required=False, allow_blank=True)
    working_hours = serializers.JSONField(required=False, allow_null=True)
    
    class Meta:
        model = TailorProfile
        fields = [
            'shop_name', 'contact_number', 'establishment_year',
            'tailor_experience', 'address', 'working_hours', 'shop_image', 'service_areas'
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
        required_fields = ['shop_name', 'address', 'service_areas']
        for field in required_fields:
            if not data.get(field):
                raise serializers.ValidationError(f"{field} is required for submission")
        
        # Check if shop_image is provided (either in data or already exists on instance)
        if not data.get('shop_image') and not (hasattr(self, 'instance') and self.instance and self.instance.shop_image):
            raise serializers.ValidationError("shop_image is required for submission")
        
        return data
