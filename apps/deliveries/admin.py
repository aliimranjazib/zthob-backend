from django.contrib import admin
from apps.deliveries.models import DeliveryTracking, LocationHistory


@admin.register(DeliveryTracking)
class DeliveryTrackingAdmin(admin.ModelAdmin):
    """Admin interface for Delivery Tracking"""
    
    list_display = [
        'id',
        'order_number',
        'rider_name',
        'current_status',
        'total_distance_km',
        'estimated_distance_km',
        'last_location_update',
        'is_active',
        'created_at',
    ]
    
    list_filter = [
        'current_status',
        'is_active',
        'created_at',
    ]
    
    search_fields = [
        'order__order_number',
        'rider__username',
        'rider__rider_profile__full_name',
        'order__customer__username',
    ]
    
    readonly_fields = [
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
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order', 'rider', 'current_status', 'is_active')
        }),
        ('Locations', {
            'fields': (
                ('pickup_latitude', 'pickup_longitude'),
                'pickup_address',
                ('delivery_latitude', 'delivery_longitude'),
                'delivery_address',
                ('last_latitude', 'last_longitude'),
            )
        }),
        ('Timestamps', {
            'fields': (
                'assigned_at',
                'accepted_at',
                'pickup_started_at',
                'picked_up_at',
                'delivery_started_at',
                'delivered_at',
            )
        }),
        ('Distance & ETA', {
            'fields': (
                'total_distance_km',
                'estimated_distance_km',
                'estimated_arrival_time',
                'last_location_update',
            )
        }),
        ('Additional Information', {
            'fields': ('notes',)
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def order_number(self, obj):
        return obj.order.order_number if obj.order else '-'
    order_number.short_description = 'Order Number'
    
    def rider_name(self, obj):
        if obj.rider:
            try:
                if hasattr(obj.rider, 'rider_profile') and obj.rider.rider_profile:
                    return obj.rider.rider_profile.full_name or obj.rider.username
                return obj.rider.username
            except:
                return obj.rider.username
        return '-'
    rider_name.short_description = 'Rider'


@admin.register(LocationHistory)
class LocationHistoryAdmin(admin.ModelAdmin):
    """Admin interface for Location History"""
    
    list_display = [
        'id',
        'delivery_tracking',
        'latitude',
        'longitude',
        'speed',
        'distance_from_previous',
        'status',
        'created_at',
    ]
    
    list_filter = [
        'status',
        'created_at',
    ]
    
    search_fields = [
        'delivery_tracking__order__order_number',
        'delivery_tracking__rider__username',
    ]
    
    readonly_fields = [
        'id',
        'created_at',
        'updated_at',
    ]
    
    fieldsets = (
        ('Tracking Information', {
            'fields': ('delivery_tracking', 'status')
        }),
        ('Location', {
            'fields': (
                ('latitude', 'longitude'),
                'accuracy',
            )
        }),
        ('Movement Data', {
            'fields': (
                'speed',
                'heading',
                'distance_from_previous',
            )
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related(
            'delivery_tracking',
            'delivery_tracking__order',
            'delivery_tracking__rider',
        )

