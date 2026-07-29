from rest_framework import serializers
from apps.core.phone_utils import display_user_label, format_phone_for_display
from apps.deliveries.models import DeliveryTracking, LocationHistory
from apps.deliveries.services import DeliveryTrackingService
from apps.orders.models import Order


def _build_rider_info(rider):
    if not rider:
        return None

    profile = getattr(rider, 'rider_profile', None)
    raw_phone = getattr(profile, 'phone_number', None) or getattr(rider, 'phone', '')
    return {
        'id': rider.id,
        'username': rider.username,
        'full_name': (
            getattr(profile, 'full_name', None)
            or rider.get_full_name()
            or rider.username
        ),
        'phone_number': format_phone_for_display(raw_phone) if raw_phone else '',
        'vehicle_type': getattr(profile, 'vehicle_type', ''),
        'rating': float(getattr(profile, 'rating', 0.0) or 0.0),
        'is_available': bool(getattr(profile, 'is_available', False)),
    }


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
        """Get rider phone (verified phone from user account)"""
        return obj.rider.phone if obj.rider else None
    
    def get_customer_name(self, obj):
        """Get customer name"""
        try:
            return obj.order.customer.username if obj.order and obj.order.customer else None
        except:
            return None
    
    def get_customer_phone(self, obj):
        """Get customer phone"""
        try:
            if obj.order and obj.order.customer and obj.order.customer.phone:
                return format_phone_for_display(obj.order.customer.phone)
        except Exception:
            return None
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
    rider_phone = serializers.SerializerMethodField()
    measurement_rider_info = serializers.SerializerMethodField()
    delivery_rider_info = serializers.SerializerMethodField()
    active_rider_info = serializers.SerializerMethodField()
    current_location = serializers.SerializerMethodField()
    estimated_time_minutes = serializers.SerializerMethodField()
    recent_route = serializers.SerializerMethodField()
    
    class Meta:
        model = DeliveryTracking
        fields = [
            'id',
            'order_number',
            'rider_name',
            'rider_phone',
            'measurement_rider_info',
            'delivery_rider_info',
            'active_rider_info',
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
    
    def _active_rider(self, obj):
        return DeliveryTrackingService.resolve_active_tracking_rider(obj.order)

    def get_rider_name(self, obj):
        """Active rider name for live tracking (delivery or measurement phase)."""
        rider = self._active_rider(obj)
        info = _build_rider_info(rider)
        return info['full_name'] if info else None
    
    def get_rider_phone(self, obj):
        """Active rider phone for live tracking."""
        rider = self._active_rider(obj)
        if rider and rider.phone:
            return format_phone_for_display(rider.phone)
        return None

    def get_measurement_rider_info(self, obj):
        """Original measurement rider — does not change when delivery rider is reassigned."""
        return _build_rider_info(obj.order.measurement_rider)

    def get_delivery_rider_info(self, obj):
        """Current delivery rider — reflects reassignments."""
        return _build_rider_info(obj.order.delivery_rider)

    def get_active_rider_info(self, obj):
        return _build_rider_info(self._active_rider(obj))
    
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

