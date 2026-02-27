"""
Services for delivery tracking calculations and utilities.
"""
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import math


class DistanceCalculationService:
    """
    Service for calculating distances between coordinates using Haversine formula.
    """
    
    EARTH_RADIUS_KM = 6371.0  # Earth's radius in kilometers
    
    @staticmethod
    def haversine_distance(lat1, lon1, lat2, lon2):
        """
        Calculate the great circle distance between two points
        on the earth (specified in decimal degrees) using Haversine formula.
        
        Returns distance in kilometers.
        """
        if not all([lat1, lon1, lat2, lon2]):
            return Decimal('0.00')
        
        # Convert decimal degrees to radians
        lat1_rad = math.radians(float(lat1))
        lon1_rad = math.radians(float(lon1))
        lat2_rad = math.radians(float(lat2))
        lon2_rad = math.radians(float(lon2))
        
        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
        c = 2 * math.asin(math.sqrt(a))
        
        distance_km = DistanceCalculationService.EARTH_RADIUS_KM * c
        
        return Decimal(str(round(distance_km, 2)))
    
    @staticmethod
    def calculate_distance_from_route(locations):
        """
        Calculate total distance from a list of location points.
        
        Args:
            locations: List of tuples (latitude, longitude)
        
        Returns:
            Total distance in kilometers
        """
        if len(locations) < 2:
            return Decimal('0.00')
        
        total_distance = Decimal('0.00')
        
        for i in range(1, len(locations)):
            lat1, lon1 = locations[i-1]
            lat2, lon2 = locations[i]
            distance = DistanceCalculationService.haversine_distance(lat1, lon1, lat2, lon2)
            total_distance += distance
        
        return total_distance


class ETACalculationService:
    """
    Service for calculating Estimated Time of Arrival (ETA).
    """
    
    # Average speeds in km/h
    AVERAGE_SPEED_KMH = Decimal('40.0')  # Average city speed
    SLOW_SPEED_KMH = Decimal('20.0')  # Traffic/slow conditions
    FAST_SPEED_KMH = Decimal('60.0')  # Highway conditions
    
    @staticmethod
    def calculate_eta(distance_km, average_speed_kmh=None):
        """
        Calculate ETA based on distance and average speed.
        
        Args:
            distance_km: Distance in kilometers
            average_speed_kmh: Average speed in km/h (optional, uses default if not provided)
        
        Returns:
            Estimated time in minutes
        """
        if not distance_km or distance_km <= 0:
            return None
        
        if average_speed_kmh is None:
            average_speed_kmh = ETACalculationService.AVERAGE_SPEED_KMH
        
        # Time = Distance / Speed (in hours)
        time_hours = float(distance_km) / float(average_speed_kmh)
        
        # Convert to minutes
        time_minutes = int(time_hours * 60)
        
        # Add buffer time (10% extra for safety)
        time_minutes = int(time_minutes * 1.1)
        
        return time_minutes
    
    @staticmethod
    def calculate_eta_datetime(distance_km, average_speed_kmh=None):
        """
        Calculate ETA as a datetime object.
        
        Args:
            distance_km: Distance in kilometers
            average_speed_kmh: Average speed in km/h (optional)
        
        Returns:
            DateTime object representing estimated arrival time
        """
        minutes = ETACalculationService.calculate_eta(distance_km, average_speed_kmh)
        
        if minutes is None:
            return None
        
        return timezone.now() + timedelta(minutes=minutes)
    
    @staticmethod
    def calculate_eta_from_speed(distance_km, current_speed_kmh=None):
        """
        Calculate ETA based on current speed if available, otherwise use average.
        
        Args:
            distance_km: Distance in kilometers
            current_speed_kmh: Current speed in km/h (optional)
        
        Returns:
            Estimated time in minutes
        """
        if current_speed_kmh and current_speed_kmh > 0:
            # Use current speed if available
            speed = Decimal(str(current_speed_kmh))
        else:
            # Use average speed
            speed = ETACalculationService.AVERAGE_SPEED_KMH
        
        return ETACalculationService.calculate_eta(distance_km, speed)


class DeliveryTrackingService:
    """
    Service for managing delivery tracking operations.
    """
    
    @staticmethod
    def create_tracking_for_order(order):
        """
        Create a delivery tracking record for an order.
        Should be called when a rider is assigned to an order.
        
        Args:
            order: Order instance
        
        Returns:
            DeliveryTracking instance
        """
        from apps.deliveries.models import DeliveryTracking
        
        if not order.rider:
            raise ValueError("Order must have a rider assigned")
        
        # Check if tracking already exists
        tracking, created = DeliveryTracking.objects.get_or_create(
            order=order,
            defaults={
                'rider': order.rider,
                'current_status': 'assigned',
                'is_active': True,
            }
        )
        
        if created:
            # Set pickup and delivery locations from order
            if order.delivery_address:
                tracking.delivery_latitude = order.delivery_address.latitude
                tracking.delivery_longitude = order.delivery_address.longitude
                tracking.delivery_address = order.delivery_address.address or str(order.delivery_address)
            
            # Try to get tailor location (if available in tailor profile)
            try:
                if hasattr(order.tailor, 'tailor_profile'):
                    # Assuming tailor profile might have location info
                    # This can be extended based on your tailor model structure
                    pass
            except:
                pass
            
            tracking.save()
        
        return tracking
    
    @staticmethod
    def update_location(tracking, latitude, longitude, accuracy=None, speed=None, heading=None, status=None):
        """
        Update rider location for a delivery tracking.
        
        Args:
            tracking: DeliveryTracking instance
            latitude: Current latitude
            longitude: Current longitude
            accuracy: Location accuracy in meters (optional)
            speed: Current speed in km/h (optional)
            heading: Heading in degrees (optional)
            status: Current status (optional)
        
        Returns:
            Tuple (LocationHistory instance, distance_from_previous)
        """
        from apps.deliveries.models import LocationHistory
        
        if not tracking.can_track:
            raise ValueError("Tracking is not active or delivery is completed")
        
        # Get previous location
        previous_location = LocationHistory.objects.filter(
            delivery_tracking=tracking
        ).order_by('-created_at').first()
        
        # Calculate distance from previous location
        distance_from_previous = Decimal('0.00')
        if previous_location:
            distance_from_previous = DistanceCalculationService.haversine_distance(
                previous_location.latitude,
                previous_location.longitude,
                latitude,
                longitude
            )
        
        # Create location history entry
        location_history = LocationHistory.objects.create(
            delivery_tracking=tracking,
            latitude=latitude,
            longitude=longitude,
            accuracy=accuracy,
            speed=speed,
            heading=heading,
            status=status or tracking.current_status,
            distance_from_previous=distance_from_previous,
        )
        
        # Update tracking with latest location
        tracking.last_latitude = latitude
        tracking.last_longitude = longitude
        tracking.last_location_update = timezone.now()
        
        # Update total distance
        tracking.total_distance_km += distance_from_previous
        
        # Calculate estimated distance to destination
        if tracking.delivery_latitude and tracking.delivery_longitude:
            estimated_distance = DistanceCalculationService.haversine_distance(
                latitude,
                longitude,
                tracking.delivery_latitude,
                tracking.delivery_longitude
            )
            tracking.estimated_distance_km = estimated_distance
            
            # Calculate ETA
            if speed and speed > 0:
                eta_datetime = ETACalculationService.calculate_eta_from_speed(
                    estimated_distance,
                    float(speed)
                )
            else:
                eta_datetime = ETACalculationService.calculate_eta_datetime(estimated_distance)
            
            tracking.estimated_arrival_time = eta_datetime
        
        tracking.save()
        
        return location_history, distance_from_previous
    
    @staticmethod
    def update_status(tracking, new_status, notes=None):
        """
        Update delivery tracking status and set appropriate timestamps.
        
        Args:
            tracking: DeliveryTracking instance
            new_status: New status string
            notes: Optional notes about the status change
        
        Returns:
            Updated DeliveryTracking instance
        """
        if not tracking.can_track:
            raise ValueError("Tracking is not active or delivery is completed")
        
        now = timezone.now()
        
        # Update status and set timestamps based on status
        if new_status == 'accepted' and not tracking.accepted_at:
            tracking.accepted_at = now
        elif new_status == 'on_way_to_pickup' and not tracking.pickup_started_at:
            tracking.pickup_started_at = now
        elif new_status == 'picked_up' and not tracking.picked_up_at:
            tracking.picked_up_at = now
        elif new_status == 'on_way_to_delivery' and not tracking.delivery_started_at:
            tracking.delivery_started_at = now
        elif new_status == 'delivered' and not tracking.delivered_at:
            tracking.delivered_at = now
            tracking.is_active = False
        elif new_status == 'cancelled':
            tracking.is_active = False
        
        tracking.current_status = new_status
        
        if notes:
            if tracking.notes:
                tracking.notes += f"\n{now.strftime('%Y-%m-%d %H:%M:%S')}: {notes}"
            else:
                tracking.notes = f"{now.strftime('%Y-%m-%d %H:%M:%S')}: {notes}"
        
        tracking.save()
        
        return tracking

