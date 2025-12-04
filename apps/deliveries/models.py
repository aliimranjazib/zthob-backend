from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.core.models import BaseModel
from decimal import Decimal


class DeliveryTracking(BaseModel):
    """
    Tracks delivery location history and status for orders.
    Stores location updates from riders and calculates ETA, distance, etc.
    """
    
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.CASCADE,
        related_name='delivery_tracking',
        help_text="Order being tracked"
    )
    
    rider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='delivery_tracks',
        help_text="Rider assigned to this delivery"
    )
    
    # Pickup location (from tailor)
    pickup_latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        help_text="Pickup location latitude (tailor location)"
    )
    
    pickup_longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        help_text="Pickup location longitude (tailor location)"
    )
    
    pickup_address = models.TextField(
        blank=True,
        null=True,
        help_text="Formatted pickup address"
    )
    
    # Delivery location (customer address)
    delivery_latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        help_text="Delivery location latitude (customer address)"
    )
    
    delivery_longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        help_text="Delivery location longitude (customer address)"
    )
    
    delivery_address = models.TextField(
        blank=True,
        null=True,
        help_text="Formatted delivery address"
    )
    
    # Current status
    current_status = models.CharField(
        max_length=30,
        choices=[
            ('assigned', 'Assigned'),
            ('accepted', 'Accepted'),
            ('on_way_to_pickup', 'On Way to Pickup'),
            ('picked_up', 'Picked Up'),
            ('on_way_to_delivery', 'On Way to Delivery'),
            ('delivered', 'Delivered'),
            ('cancelled', 'Cancelled'),
        ],
        default='assigned',
        help_text="Current delivery status"
    )
    
    # Timestamps for key events
    assigned_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When rider was assigned"
    )
    
    accepted_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When rider accepted the order"
    )
    
    pickup_started_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When rider started heading to pickup location"
    )
    
    picked_up_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When rider picked up the order"
    )
    
    delivery_started_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When rider started heading to delivery location"
    )
    
    delivered_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When order was delivered"
    )
    
    # Distance tracking
    total_distance_km = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total distance traveled in kilometers"
    )
    
    estimated_distance_km = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Estimated distance from current location to destination in km"
    )
    
    # ETA (Estimated Time of Arrival)
    estimated_arrival_time = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Estimated time of arrival at destination"
    )
    
    # Last location update
    last_latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        help_text="Last known latitude"
    )
    
    last_longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        help_text="Last known longitude"
    )
    
    last_location_update = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When last location was updated"
    )
    
    # Additional info
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Additional notes about the delivery"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this tracking is currently active"
    )
    
    class Meta:
        verbose_name = "Delivery Tracking"
        verbose_name_plural = "Delivery Tracking"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order', 'is_active']),
            models.Index(fields=['rider', 'is_active']),
            models.Index(fields=['last_location_update']),
        ]
    
    def __str__(self):
        return f"Tracking for Order {self.order.order_number} - {self.current_status}"
    
    @property
    def is_completed(self):
        """Check if delivery is completed"""
        return self.current_status == 'delivered' or self.current_status == 'cancelled'
    
    @property
    def can_track(self):
        """Check if tracking is still active and can be updated"""
        return self.is_active and not self.is_completed


class LocationHistory(BaseModel):
    """
    Stores historical location updates for delivery tracking.
    This allows us to show the route taken by the rider.
    Automatically cleaned up after 30 days.
    """
    
    delivery_tracking = models.ForeignKey(
        DeliveryTracking,
        on_delete=models.CASCADE,
        related_name='location_history',
        help_text="Delivery tracking this location belongs to"
    )
    
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        help_text="Latitude coordinate"
    )
    
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        help_text="Longitude coordinate"
    )
    
    accuracy = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Location accuracy in meters (if available)"
    )
    
    speed = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Speed in km/h (if available)"
    )
    
    heading = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Heading/bearing in degrees (0-360)"
    )
    
    status = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        help_text="Rider status at this location"
    )
    
    distance_from_previous = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Distance from previous location in km"
    )
    
    class Meta:
        verbose_name = "Location History"
        verbose_name_plural = "Location Histories"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['delivery_tracking', '-created_at']),
            models.Index(fields=['created_at']),  # For cleanup queries
        ]
    
    def __str__(self):
        return f"Location ({self.latitude}, {self.longitude}) at {self.created_at}"

