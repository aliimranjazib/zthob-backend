from rest_framework import serializers
from apps.deliveries.models import DeliveryTracking, LocationHistory
from apps.orders.models import Order


class LocationHistorySerializer(serializers.ModelSerializer):
    """Serializer for location history entries"""
    
    class Meta:
        model = LocationHistory
        fields = [
            'id',
            'latitude',
            'longitude',
            'accuracy',
            'speed',
            'heading',
            'status',
            'distance_from_previous',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class DeliveryTrackingSerializer(serializers.ModelSerializer):
    """Serializer for delivery tracking data"""
    
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    rider_name = serializers.SerializerMethodField()
    rider_phone = serializers.SerializerMethodField()
    customer_name = serializers.SerializerMethodField()
    customer_phone = serializers.SerializerMethodField()
    
    class Meta:
        model = DeliveryTracking
        fields = [
            'id',
            'order',
            'order_number',
            'rider',
            'rider_name',
            'rider_phone',
            'customer_name',
            'customer_phone',
            'pickup_latitude',
            'pickup_longitude',
            'pickup_address',
            'delivery_latitude',
            'delivery_longitude',
            'delivery_address',
            'current_status',
            'assigned_at',
            'accepted_at',
            'pickup_started_at',
            'picked_up_at',
            'delivery_started_at',
            'delivered_at',
            'total_distance_km',
            'estimated_distance_km',
            'estimated_arrival_time',
            'last_latitude',
            'last_longitude',
            'last_location_update',
            'notes',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'assigned_at',
            'accepted_at',
            'pickup_started_at',
            'picked_up_at',
            'delivery_started_at',
            'delivered_at',
            'total_distance_km',
            'estimated_distance_km',
            'estimated_arrival_time',
            'last_location_update',
            'created_at',
            'updated_at',
        ]
    
    def get_rider_name(self, obj):
        """Get rider name"""
        try:
            if hasattr(obj.rider, 'rider_profile') and obj.rider.rider_profile:
                return obj.rider.rider_profile.full_name or obj.rider.username
            return obj.rider.username
        except:
            return obj.rider.username if obj.rider else None
    
    def get_rider_phone(self, obj):
        """Get rider phone"""
        try:
            if hasattr(obj.rider, 'rider_profile') and obj.rider.rider_profile:
                return obj.rider.rider_profile.phone_number
            return obj.rider.phone_number if hasattr(obj.rider, 'phone_number') else None
        except:
            return None
    
    def get_customer_name(self, obj):
        """Get customer name"""
        try:
            return obj.order.customer.username if obj.order and obj.order.customer else None
        except:
            return None
    
    def get_customer_phone(self, obj):
        """Get customer phone"""
        try:
            return obj.order.customer.phone_number if obj.order and hasattr(obj.order.customer, 'phone_number') else None
        except:
            return None


class DeliveryTrackingDetailSerializer(DeliveryTrackingSerializer):
    """Detailed serializer with location history"""
    
    location_history = LocationHistorySerializer(many=True, read_only=True)
    recent_locations = serializers.SerializerMethodField()
    
    class Meta(DeliveryTrackingSerializer.Meta):
        fields = DeliveryTrackingSerializer.Meta.fields + [
            'location_history',
            'recent_locations',
        ]
    
    def get_recent_locations(self, obj):
        """Get recent location history (last 50 points)"""
        recent = obj.location_history.all()[:50]
        return LocationHistorySerializer(recent, many=True).data


class RiderLocationUpdateSerializer(serializers.Serializer):
    """Serializer for rider location updates"""
    
    latitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        required=True,
        help_text="Current latitude"
    )
    
    longitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        required=True,
        help_text="Current longitude"
    )
    
    accuracy = serializers.DecimalField(
        max_digits=8,
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text="Location accuracy in meters"
    )
    
    speed = serializers.DecimalField(
        max_digits=8,
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text="Current speed in km/h"
    )
    
    heading = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text="Heading/bearing in degrees (0-360)"
    )
    
    status = serializers.CharField(
        max_length=30,
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text="Current rider status (optional)"
    )
    
    def validate_latitude(self, value):
        """Validate latitude is within valid range"""
        if value < -90 or value > 90:
            raise serializers.ValidationError("Latitude must be between -90 and 90")
        return value
    
    def validate_longitude(self, value):
        """Validate longitude is within valid range"""
        if value < -180 or value > 180:
            raise serializers.ValidationError("Longitude must be between -180 and 180")
        return value
    
    def validate_heading(self, value):
        """Validate heading is within valid range"""
        if value is not None and (value < 0 or value > 360):
            raise serializers.ValidationError("Heading must be between 0 and 360")
        return value


class CustomerTrackingSerializer(serializers.ModelSerializer):
    """Simplified serializer for customer tracking view"""
    
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    rider_name = serializers.SerializerMethodField()
    current_location = serializers.SerializerMethodField()
    estimated_time_minutes = serializers.SerializerMethodField()
    recent_route = serializers.SerializerMethodField()
    
    class Meta:
        model = DeliveryTracking
        fields = [
            'id',
            'order_number',
            'rider_name',
            'current_status',
            'current_location',
            'delivery_address',
            'estimated_distance_km',
            'estimated_time_minutes',
            'estimated_arrival_time',
            'total_distance_km',
            'picked_up_at',
            'delivery_started_at',
            'recent_route',
            'last_location_update',
        ]
        read_only_fields = ['id']
    
    def get_rider_name(self, obj):
        """Get rider name"""
        try:
            if hasattr(obj.rider, 'rider_profile') and obj.rider.rider_profile:
                return obj.rider.rider_profile.full_name or obj.rider.username
            return obj.rider.username
        except:
            return obj.rider.username if obj.rider else None
    
    def get_current_location(self, obj):
        """Get current rider location"""
        if obj.last_latitude and obj.last_longitude:
            return {
                'latitude': float(obj.last_latitude),
                'longitude': float(obj.last_longitude),
                'updated_at': obj.last_location_update.isoformat() if obj.last_location_update else None,
            }
        return None
    
    def get_estimated_time_minutes(self, obj):
        """Calculate estimated time in minutes"""
        if obj.estimated_arrival_time:
            from django.utils import timezone
            now = timezone.now()
            if obj.estimated_arrival_time > now:
                delta = obj.estimated_arrival_time - now
                return int(delta.total_seconds() / 60)
        return None
    
    def get_recent_route(self, obj):
        """Get recent route points (last 20)"""
        recent = obj.location_history.all()[:20]
        return [
            {
                'latitude': float(loc.latitude),
                'longitude': float(loc.longitude),
                'timestamp': loc.created_at.isoformat(),
            }
            for loc in recent
        ]

