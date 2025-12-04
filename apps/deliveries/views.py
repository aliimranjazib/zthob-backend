from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db.models import Q
from drf_spectacular.utils import extend_schema
from zthob.utils import api_response

from apps.orders.models import Order
from apps.deliveries.models import DeliveryTracking, LocationHistory
from apps.deliveries.serializers import (
    DeliveryTrackingSerializer,
    DeliveryTrackingDetailSerializer,
    RiderLocationUpdateSerializer,
    CustomerTrackingSerializer,
    LocationHistorySerializer,
)
from apps.deliveries.services import (
    DeliveryTrackingService,
    DistanceCalculationService,
    ETACalculationService,
)


# ============================================================================
# RIDER ENDPOINTS
# ============================================================================

class RiderUpdateLocationView(APIView):
    """
    Endpoint for riders to update their current location during delivery.
    Should be called every 15 seconds when actively delivering.
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        request=RiderLocationUpdateSerializer,
        responses={200: DeliveryTrackingSerializer},
        summary="Update rider location",
        description="Update current location for an active delivery. Call every 15 seconds during active delivery.",
        tags=["Rider Delivery Tracking"],
        parameters=[
            {
                'name': 'order_id',
                'in': 'path',
                'required': True,
                'description': 'Order ID',
                'schema': {'type': 'integer'}
            }
        ]
    )
    def post(self, request, order_id):
        """Update rider location for an order"""
        
        # Get order
        order = get_object_or_404(Order, id=order_id)
        
        # Verify rider is assigned to this order
        if order.rider != request.user:
            return api_response(
                success=False,
                message="You are not assigned to this order",
                status_code=status.HTTP_403_FORBIDDEN,
                request=request
            )
        
        # Verify user is a rider
        if request.user.role != 'RIDER':
            return api_response(
                success=False,
                message="Only riders can update location",
                status_code=status.HTTP_403_FORBIDDEN,
                request=request
            )
        
        # Get or create tracking
        try:
            tracking = DeliveryTracking.objects.get(order=order, rider=request.user, is_active=True)
        except DeliveryTracking.DoesNotExist:
            # Create tracking if it doesn't exist
            tracking = DeliveryTrackingService.create_tracking_for_order(order)
        
        # Validate location data
        serializer = RiderLocationUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(
                success=False,
                message="Invalid location data",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
                request=request
            )
        
        # Update location
        try:
            location_history, distance = DeliveryTrackingService.update_location(
                tracking=tracking,
                latitude=serializer.validated_data['latitude'],
                longitude=serializer.validated_data['longitude'],
                accuracy=serializer.validated_data.get('accuracy'),
                speed=serializer.validated_data.get('speed'),
                heading=serializer.validated_data.get('heading'),
                status=serializer.validated_data.get('status'),
            )
            
            # Refresh tracking
            tracking.refresh_from_db()
            
            return api_response(
                success=True,
                message="Location updated successfully",
                data={
                    'tracking': DeliveryTrackingSerializer(tracking, context={'request': request}).data,
                    'distance_from_previous_km': float(distance),
                },
                status_code=status.HTTP_200_OK,
                request=request
            )
        except ValueError as e:
            return api_response(
                success=False,
                message=str(e),
                status_code=status.HTTP_400_BAD_REQUEST,
                request=request
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Location update error: {str(e)}", exc_info=True)
            
            return api_response(
                success=False,
                message="Failed to update location",
                errors=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                request=request
            )


class RiderTrackingView(APIView):
    """
    Get tracking information for a specific order (rider view).
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        responses={200: DeliveryTrackingDetailSerializer},
        summary="Get delivery tracking (rider)",
        description="Get detailed tracking information for an order assigned to the rider",
        tags=["Rider Delivery Tracking"],
        parameters=[
            {
                'name': 'order_id',
                'in': 'path',
                'required': True,
                'description': 'Order ID',
                'schema': {'type': 'integer'}
            }
        ]
    )
    def get(self, request, order_id):
        """Get tracking information"""
        
        # Get order
        order = get_object_or_404(Order, id=order_id)
        
        # Verify rider is assigned
        if order.rider != request.user:
            return api_response(
                success=False,
                message="You are not assigned to this order",
                status_code=status.HTTP_403_FORBIDDEN,
                request=request
            )
        
        # Get tracking
        try:
            tracking = DeliveryTracking.objects.get(order=order, rider=request.user)
        except DeliveryTracking.DoesNotExist:
            # Create if doesn't exist
            tracking = DeliveryTrackingService.create_tracking_for_order(order)
        
        serializer = DeliveryTrackingDetailSerializer(tracking, context={'request': request})
        
        return api_response(
            success=True,
            message="Tracking information retrieved successfully",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
            request=request
        )


# ============================================================================
# CUSTOMER ENDPOINTS
# ============================================================================

class CustomerTrackingView(APIView):
    """
    Get delivery tracking information for customer's order.
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        responses={200: CustomerTrackingSerializer},
        summary="Get delivery tracking (customer)",
        description="Get real-time delivery tracking information for customer's order",
        tags=["Customer Delivery Tracking"],
        parameters=[
            {
                'name': 'order_id',
                'in': 'path',
                'required': True,
                'description': 'Order ID',
                'schema': {'type': 'integer'}
            }
        ]
    )
    def get(self, request, order_id):
        """Get tracking information for customer"""
        
        # Get order
        order = get_object_or_404(Order, id=order_id)
        
        # Verify customer owns this order
        if order.customer != request.user:
            return api_response(
                success=False,
                message="You can only track your own orders",
                status_code=status.HTTP_403_FORBIDDEN,
                request=request
            )
        
        # Check if order has a rider assigned
        if not order.rider:
            return api_response(
                success=False,
                message="No rider assigned to this order yet",
                status_code=status.HTTP_404_NOT_FOUND,
                request=request
            )
        
        # Get tracking
        try:
            tracking = DeliveryTracking.objects.get(order=order, is_active=True)
        except DeliveryTracking.DoesNotExist:
            # Create if doesn't exist
            tracking = DeliveryTrackingService.create_tracking_for_order(order)
        
        serializer = CustomerTrackingSerializer(tracking, context={'request': request})
        
        return api_response(
            success=True,
            message="Tracking information retrieved successfully",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
            request=request
        )


class CustomerTrackingHistoryView(APIView):
    """
    Get location history for customer's order.
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        responses={200: LocationHistorySerializer(many=True)},
        summary="Get location history (customer)",
        description="Get location history for customer's order delivery",
        tags=["Customer Delivery Tracking"],
        parameters=[
            {
                'name': 'order_id',
                'in': 'path',
                'required': True,
                'description': 'Order ID',
                'schema': {'type': 'integer'}
            },
            {
                'name': 'limit',
                'in': 'query',
                'required': False,
                'description': 'Number of location points to return (default: 50)',
                'schema': {'type': 'integer', 'default': 50}
            }
        ]
    )
    def get(self, request, order_id):
        """Get location history"""
        
        # Get order
        order = get_object_or_404(Order, id=order_id)
        
        # Verify customer owns this order
        if order.customer != request.user:
            return api_response(
                success=False,
                message="You can only track your own orders",
                status_code=status.HTTP_403_FORBIDDEN,
                request=request
            )
        
        # Get tracking
        try:
            tracking = DeliveryTracking.objects.get(order=order)
        except DeliveryTracking.DoesNotExist:
            return api_response(
                success=False,
                message="No tracking data available for this order",
                status_code=status.HTTP_404_NOT_FOUND,
                request=request
            )
        
        # Get location history
        limit = int(request.query_params.get('limit', 50))
        location_history = tracking.location_history.all()[:limit]
        
        serializer = LocationHistorySerializer(location_history, many=True)
        
        return api_response(
            success=True,
            message="Location history retrieved successfully",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
            request=request
        )


# ============================================================================
# ADMIN/TAILOR ENDPOINTS
# ============================================================================

class AdminTrackingView(APIView):
    """
    Get detailed delivery tracking information (admin/tailor view).
    Shows full tracking details including all location history.
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        responses={200: DeliveryTrackingDetailSerializer},
        summary="Get delivery tracking (admin/tailor)",
        description="Get detailed delivery tracking information. Accessible by admin, tailor, or rider assigned to the order.",
        tags=["Admin Delivery Tracking"],
        parameters=[
            {
                'name': 'order_id',
                'in': 'path',
                'required': True,
                'description': 'Order ID',
                'schema': {'type': 'integer'}
            }
        ]
    )
    def get(self, request, order_id):
        """Get detailed tracking information"""
        
        # Get order
        order = get_object_or_404(Order, id=order_id)
        
        # Check permissions
        user_role = request.user.role
        has_access = False
        
        if user_role == 'ADMIN':
            has_access = True
        elif user_role == 'TAILOR' and order.tailor == request.user:
            has_access = True
        elif user_role == 'RIDER' and order.rider == request.user:
            has_access = True
        
        if not has_access:
            return api_response(
                success=False,
                message="You do not have permission to view this tracking information",
                status_code=status.HTTP_403_FORBIDDEN,
                request=request
            )
        
        # Get tracking
        try:
            tracking = DeliveryTracking.objects.get(order=order)
        except DeliveryTracking.DoesNotExist:
            # Create if doesn't exist and order has rider
            if order.rider:
                tracking = DeliveryTrackingService.create_tracking_for_order(order)
            else:
                return api_response(
                    success=False,
                    message="No tracking data available. Order has no rider assigned.",
                    status_code=status.HTTP_404_NOT_FOUND,
                    request=request
                )
        
        serializer = DeliveryTrackingDetailSerializer(tracking, context={'request': request})
        
        return api_response(
            success=True,
            message="Tracking information retrieved successfully",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
            request=request
        )


class AdminTrackingRouteView(APIView):
    """
    Get route visualization data for admin dashboard.
    Returns all location points for route mapping.
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        responses={200: {'type': 'object'}},
        summary="Get delivery route data",
        description="Get route visualization data for admin dashboard. Returns all location points for mapping.",
        tags=["Admin Delivery Tracking"],
        parameters=[
            {
                'name': 'order_id',
                'in': 'path',
                'required': True,
                'description': 'Order ID',
                'schema': {'type': 'integer'}
            }
        ]
    )
    def get(self, request, order_id):
        """Get route data for visualization"""
        
        # Get order
        order = get_object_or_404(Order, id=order_id)
        
        # Check permissions (admin or tailor)
        user_role = request.user.role
        if user_role not in ['ADMIN', 'TAILOR']:
            return api_response(
                success=False,
                message="Only admin and tailor can view route data",
                status_code=status.HTTP_403_FORBIDDEN,
                request=request
            )
        
        if user_role == 'TAILOR' and order.tailor != request.user:
            return api_response(
                success=False,
                message="You can only view route data for your own orders",
                status_code=status.HTTP_403_FORBIDDEN,
                request=request
            )
        
        # Get tracking
        try:
            tracking = DeliveryTracking.objects.get(order=order)
        except DeliveryTracking.DoesNotExist:
            return api_response(
                success=False,
                message="No tracking data available for this order",
                status_code=status.HTTP_404_NOT_FOUND,
                request=request
            )
        
        # Get all location points
        locations = tracking.location_history.all().order_by('created_at')
        
        route_data = {
            'order_id': order.id,
            'order_number': order.order_number,
            'pickup_location': {
                'latitude': float(tracking.pickup_latitude) if tracking.pickup_latitude else None,
                'longitude': float(tracking.pickup_longitude) if tracking.pickup_longitude else None,
                'address': tracking.pickup_address,
            },
            'delivery_location': {
                'latitude': float(tracking.delivery_latitude) if tracking.delivery_latitude else None,
                'longitude': float(tracking.delivery_longitude) if tracking.delivery_longitude else None,
                'address': tracking.delivery_address,
            },
            'current_location': {
                'latitude': float(tracking.last_latitude) if tracking.last_latitude else None,
                'longitude': float(tracking.last_longitude) if tracking.last_longitude else None,
                'updated_at': tracking.last_location_update.isoformat() if tracking.last_location_update else None,
            },
            'route_points': [
                {
                    'latitude': float(loc.latitude),
                    'longitude': float(loc.longitude),
                    'timestamp': loc.created_at.isoformat(),
                    'speed': float(loc.speed) if loc.speed else None,
                    'heading': float(loc.heading) if loc.heading else None,
                }
                for loc in locations
            ],
            'total_distance_km': float(tracking.total_distance_km),
            'estimated_distance_km': float(tracking.estimated_distance_km) if tracking.estimated_distance_km else None,
            'current_status': tracking.current_status,
            'estimated_arrival_time': tracking.estimated_arrival_time.isoformat() if tracking.estimated_arrival_time else None,
        }
        
        return api_response(
            success=True,
            message="Route data retrieved successfully",
            data=route_data,
            status_code=status.HTTP_200_OK,
            request=request
        )

