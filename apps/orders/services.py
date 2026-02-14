from decimal import Decimal
from django.db import transaction
from django.conf import settings
from django.core.exceptions import ValidationError
from apps.tailors.models import Fabric,TailorProfile
from apps.core.models import SystemSettings

class OrderCalculationService:

    """
    Service for calculating order totals and handling order business logic.
    Uses SystemSettings for dynamic configuration.
    """

    @staticmethod
    def get_system_settings():
        """Get active system settings"""
        return SystemSettings.get_active_settings()

    @staticmethod
    def calculate_subtotal(items_data):
        """Calculate subtotal from items"""
        subtotal=Decimal('0.00')
        for item in items_data:
            fabric=item['fabric']
            quantity=Decimal(str(item.get('quantity',1)))
            unit_price=fabric.price
            subtotal+=unit_price*quantity
        return subtotal.quantize(Decimal('0.01'))
    
    @staticmethod
    def calculate_tax(subtotal, tax_rate=None):
        """Calculate tax amount"""
        if tax_rate is None:
            system_settings = OrderCalculationService.get_system_settings()
            tax_rate = system_settings.tax_rate
        
        if subtotal<=0:
            return Decimal('0.00')
        tax_amount=subtotal * tax_rate
        return tax_amount.quantize(Decimal('0.01'))

    @staticmethod
    def calculate_delivery_fee(subtotal, distance_km=None, delivery_address=None, tailor=None, delivery_latitude=None, delivery_longitude=None):
        """
        Calculate delivery fee based on distance and order subtotal.
        
        Args:
            subtotal: Order subtotal amount
            distance_km: Distance in kilometers (optional, will be calculated if not provided)
            delivery_address: Delivery address object (optional)
            tailor: Tailor object (optional, used to get tailor's location)
            delivery_latitude: Delivery latitude (optional)
            delivery_longitude: Delivery longitude (optional)
        """
        system_settings = OrderCalculationService.get_system_settings()
        
        # Check for free delivery threshold
        if system_settings.free_delivery_threshold > 0:
            if subtotal >= system_settings.free_delivery_threshold:
                return Decimal('0.00')
        
        # If distance is not provided, try to calculate it on the backend
        if distance_km is None:
            # Get customer coordinates
            cust_lat = None
            cust_lng = None
            
            if delivery_latitude is not None and delivery_longitude is not None:
                cust_lat = delivery_latitude
                cust_lng = delivery_longitude
            elif delivery_address:
                cust_lat = delivery_address.latitude
                cust_lng = delivery_address.longitude
            
            # Get tailor coordinates
            tailor_lat = None
            tailor_lng = None
            
            if tailor:
                # Get tailor's default address
                from apps.customers.models import Address
                tailor_address = Address.objects.filter(user=tailor, is_default=True).first()
                if not tailor_address:
                    # Try any address if no default
                    tailor_address = Address.objects.filter(user=tailor).first()
                
                if tailor_address:
                    tailor_lat = tailor_address.latitude
                    tailor_lng = tailor_address.longitude
            
            # If we have both coordinates, calculate distance
            if all([cust_lat, cust_lng, tailor_lat, tailor_lng]):
                from apps.deliveries.services import DistanceCalculationService
                distance_km = DistanceCalculationService.haversine_distance(
                    cust_lat, cust_lng, tailor_lat, tailor_lng
                )
        
        # Calculate based on distance if we have it now (either provided or calculated)
        if distance_km is not None:
            if distance_km < system_settings.distance_threshold_km:
                return system_settings.delivery_fee_under_10km
            else:
                return system_settings.delivery_fee_10km_and_above
        
        # Fallback to default (under 10km fee) if distance still missing
        return system_settings.delivery_fee_under_10km

    @staticmethod
    def calculate_stitching_price(items_data, order_type):
        """
        Calculate stitching price from fabric items.
        
        Args:
            items_data: List of items with fabric and quantity
            order_type: Type of order ('fabric_only' or 'fabric_with_stitching')
        
        Returns:
            Decimal: Total stitching price
        """
        if order_type != 'fabric_with_stitching':
            return Decimal('0.00')
        
        stitching_total = Decimal('0.00')
        for item in items_data:
            fabric = item['fabric']
            quantity = Decimal(str(item.get('quantity', 1)))
            
            # Get stitching price from fabric (from tailor)
            if fabric.stitching_price is not None:
                stitching_total += fabric.stitching_price * quantity
        
        return stitching_total.quantize(Decimal('0.01'))

    @staticmethod
    def calculate_all_totals(items_data, distance_km=None, delivery_address=None, tailor=None, tax_rate=None, order_type='fabric_only', service_mode='home_delivery', delivery_latitude=None, delivery_longitude=None):
        """
        Calculate all order totals.
        
        Args:
            items_data: List of items with fabric and quantity
            distance_km: Distance in kilometers for delivery fee calculation
            delivery_address: Delivery address (optional)
            tailor: Tailor object (optional)
            tax_rate: Custom tax rate (optional, uses system settings if not provided)
            order_type: Type of order ('fabric_only' or 'fabric_with_stitching') - determines if stitching price is included
            service_mode: Service mode ('home_delivery' or 'walk_in') - determines if delivery fee is charged
            delivery_latitude: Delivery latitude (optional)
            delivery_longitude: Delivery longitude (optional)
        """ 
        # For measurement service orders, all costs are zero
        if order_type == 'measurement_service':
            return {
                'subtotal': Decimal('0.00'),
                'stitching_price': Decimal('0.00'),
                'tax_amount': Decimal('0.00'),
                'delivery_fee': Decimal('0.00'),
                'system_fee': Decimal('0.00'),
                'total_amount': Decimal('0.00'),
            }
        
        subtotal = OrderCalculationService.calculate_subtotal(items_data)
        
        # Calculate stitching price if order type is fabric_with_stitching
        stitching_price = OrderCalculationService.calculate_stitching_price(items_data, order_type)
        
        # Subtotal includes fabric price, stitching price is added separately
        # Tax is calculated on subtotal (fabric price only)
        tax_amount = OrderCalculationService.calculate_tax(subtotal, tax_rate)
        
        # Delivery fee is calculated on subtotal (fabric price only)
        # Skip delivery fee for walk-in orders
        if service_mode == 'walk_in':
            delivery_fee = Decimal('0.00')
        else:
            delivery_fee = OrderCalculationService.calculate_delivery_fee(
                subtotal, 
                distance_km=distance_km,
                delivery_address=delivery_address,
                tailor=tailor,
                delivery_latitude=delivery_latitude,
                delivery_longitude=delivery_longitude
            )
        
        # Total includes: subtotal (fabric) + stitching_price + tax + delivery_fee
        system_fee = Decimal('0.00')
        if order_type == 'fabric_with_stitching' and service_mode != 'walk_in':
            system_settings = OrderCalculationService.get_system_settings()
            system_fee = system_settings.system_fee_amount
        
        # Total includes: subtotal (fabric) + stitching_price + tax + delivery_fee + system_fee
        total_amount = subtotal + stitching_price + tax_amount + delivery_fee + system_fee
        
        return {
            'subtotal': subtotal,
            'stitching_price': stitching_price,
            'tax_amount': tax_amount,
            'delivery_fee': delivery_fee,
            'system_fee': system_fee,
            'total_amount': total_amount.quantize(Decimal('0.01'))
        }


class AdminAnalyticsService:
    """
    Service for calculating global system analytics for Admin Dashboard.
    Provides financial breakdown, order status tracking, and transaction summaries.
    """

    @staticmethod
    def get_dashboard_stats(start_date=None, end_date=None):
        """
        Get global dashboard statistics.
        
        Args:
            start_date: Optional filter for order creation
            end_date: Optional filter for order creation
        """
        queryset = Order.objects.all()
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)

        # 1. Order Status Snapshot
        status_counts = queryset.values('status').annotate(count=Count('id')).order_by('status')
        status_map = {item['status']: item['count'] for item in status_counts}

        # 2. Financial Breakdown (Successful Orders only)
        # We consider delivered, ready_for_delivery, ready_for_pickup, and collected as "revenue generating"
        revenue_queryset = queryset.filter(status__in=['delivered', 'ready_for_delivery', 'ready_for_pickup', 'collected', 'in_progress'])
        
        financials = revenue_queryset.aggregate(
            total_gross=Sum('total_amount'),
            total_subtotal=Sum('subtotal'),
            total_stitching=Sum('stitching_price'),
            total_tax=Sum('tax_amount'),
            total_delivery_fees=Sum('delivery_fee'),
            total_system_fees=Sum('system_fee'),
            order_count=Count('id')
        )

        # 3. Payment Method Breakdown
        payment_breakdown = queryset.values('payment_method').annotate(
            count=Count('id'),
            total=Sum('total_amount')
        ).order_by('-total')

        # 4. Daily Trends (Last 7 days)
        today = timezone.now().date()
        seven_days_ago = today - timedelta(days=7)
        daily_trends = queryset.filter(created_at__date__gte=seven_days_ago).extra(
            select={'day': "date(created_at)"}
        ).values('day').annotate(
            count=Count('id'),
            revenue=Sum('total_amount')
        ).order_by('day')

        return {
            'overview': {
                'total_orders': queryset.count(),
                'active_orders': queryset.exclude(status__in=['delivered', 'cancelled', 'collected']).count(),
                'completed_orders': queryset.filter(status__in=['delivered', 'collected']).count(),
                'cancelled_orders': queryset.filter(status='cancelled').count(),
            },
            'financials': {
                'gross_revenue': financials['total_gross'] or Decimal('0.00'),
                'fabric_revenue': financials['total_subtotal'] or Decimal('0.00'),
                'stitching_revenue': financials['total_stitching'] or Decimal('0.00'),
                'tax_collected': financials['total_tax'] or Decimal('0.00'),
                'delivery_fees': financials['total_delivery_fees'] or Decimal('0.00'),
                'system_fees': financials['total_system_fees'] or Decimal('0.00'), # The 3 SAR fee
            },
            'status_breakdown': status_map,
            'payment_method_breakdown': list(payment_breakdown),
            'daily_trends': list(daily_trends),
            'generated_at': timezone.now().isoformat()
        }


class OrderStatusTransitionService:
    """
    Centralized service for managing order status transitions.
    Handles role-based permissions and order type specific flows.
    """
    
    # Role definitions
    ROLE_TAILOR = 'TAILOR'
    ROLE_RIDER = 'RIDER'
    ROLE_USER = 'USER'
    ROLE_ADMIN = 'ADMIN'
    
    @staticmethod
    def get_allowed_transitions(order, user_role):
        """
        Get allowed status transitions for a given order and user role.
        
        Returns:
            dict: {
                'status': [list of allowed main statuses],
                'rider_status': [list of allowed rider statuses],
                'tailor_status': [list of allowed tailor statuses]
            }
        """
        if order.status == 'delivered' or order.status == 'cancelled':
            return {'status': [], 'rider_status': [], 'tailor_status': []}
        
        # Handle measurement service orders specifically
        if order.order_type == 'measurement_service':
            return OrderStatusTransitionService._get_measurement_service_transitions(order, user_role)
        
        if order.service_mode == 'walk_in':
            return OrderStatusTransitionService._get_walk_in_transitions(order, user_role)
        
        if order.order_type == 'fabric_only':
            return OrderStatusTransitionService._get_walk_in_transitions(order, user_role) if order.service_mode == 'walk_in' else OrderStatusTransitionService._get_fabric_only_transitions(order, user_role)
        else:  # fabric_with_stitching
            return OrderStatusTransitionService._get_fabric_with_stitching_transitions(order, user_role)
    
    @staticmethod
    def _get_fabric_only_transitions(order, user_role):
        """Get transitions for fabric_only orders"""
        transitions = {'status': [], 'rider_status': [], 'tailor_status': []}
        
        if user_role == OrderStatusTransitionService.ROLE_ADMIN:
            # Admin can do everything
            transitions['status'] = ['confirmed', 'in_progress', 'ready_for_delivery', 'delivered', 'cancelled']
            transitions['rider_status'] = ['accepted', 'on_way_to_pickup', 'picked_up', 'on_way_to_delivery', 'delivered']
            transitions['tailor_status'] = ['accepted']
        elif user_role == OrderStatusTransitionService.ROLE_TAILOR:
            # Require rider to accept before tailor can progress (except initial accept)
            if order.rider_status == 'none':
                if order.tailor_status == 'none':
                    # Tailor can only accept the order; no status change yet
                    transitions['tailor_status'] = ['accepted']
                # If tailor has already accepted but rider hasn't, tailor must wait
                return transitions
            
            if order.status == 'pending':
                transitions['status'] = ['confirmed']
                if order.tailor_status == 'none':
                    transitions['tailor_status'] = ['accepted']
            elif order.status == 'confirmed':
                # Allow tailor to accept if not yet accepted
                if order.tailor_status == 'none':
                    transitions['tailor_status'] = ['accepted']
                transitions['status'] = ['in_progress']
            elif order.status == 'in_progress':
                # Allow tailor to accept if not yet accepted (for orders created before fix)
                if order.tailor_status == 'none':
                    transitions['tailor_status'] = ['accepted']
                transitions['status'] = ['ready_for_delivery']
            elif order.status == 'ready_for_delivery':
                # Tailor can't change status once ready for delivery
                pass
        elif user_role == OrderStatusTransitionService.ROLE_RIDER:
            # Rider can accept order if tailor has already accepted (tailor_status == 'accepted')
            if order.rider_status == 'none' and order.tailor_status == 'accepted':
                transitions['rider_status'] = ['accepted']
            elif order.rider_status == 'accepted':
                transitions['rider_status'] = ['on_way_to_pickup']
            elif order.rider_status == 'on_way_to_pickup':
                transitions['rider_status'] = ['picked_up']
            elif order.rider_status == 'picked_up':
                transitions['rider_status'] = ['on_way_to_delivery']
            elif order.rider_status == 'on_way_to_delivery':
                transitions['rider_status'] = ['delivered']
                transitions['status'] = ['delivered']
        elif user_role == OrderStatusTransitionService.ROLE_USER:
            if order.status == 'pending':
                transitions['status'] = ['cancelled']
        
        return transitions
    
    @staticmethod
    def _get_measurement_service_transitions(order, user_role):
        """
        Get allowed transitions for measurement_service orders.
        Walk-in: Tailor takes measurements
        Home delivery: Rider takes measurements
        """
        transitions = {'status': [], 'rider_status': [], 'tailor_status': [], 'custom_actions': []}
        
        if user_role == OrderStatusTransitionService.ROLE_TAILOR:
            if order.service_mode == 'walk_in':
                # Walk-in measurement flow for tailor
                if order.tailor_status == 'none' and order.status == 'pending':
                    transitions['tailor_status'] = ['accepted']
                
                elif order.tailor_status == 'accepted':
                    # After accepting, check if measurements are recorded
                    # Check if all items have non-empty measurements
                    all_measured = True
                    if order.order_items.count() == 0:
                        all_measured = False
                    else:
                        for item in order.order_items.all():
                            if not item.measurements or len(item.measurements) == 0:
                                all_measured = False
                                break
                    
                    if all_measured:
                        # All measurements recorded, can mark as complete
                        transitions['tailor_status'] = ['measurements_complete']
                    else:
                        # Need to record measurements first
                        transitions['custom_actions'] = [{
                            "type": "form_action", 
                            "value": "record_measurements",
                            "label": "Record Measurements",
                            "description": "Open measurement form to record customer measurements"
                        }]
                
        elif user_role == OrderStatusTransitionService.ROLE_RIDER:
            if order.service_mode == 'home_delivery':
                # Home delivery measurement flow for rider
                if order.rider_status == 'none' and order.status == 'pending':
                    transitions['rider_status'] = ['accepted']
                
                elif order.rider_status == 'accepted':
                    transitions['rider_status'] = ['on_way_to_measurement']
                
                elif order.rider_status == 'on_way_to_measurement':
                    transitions['rider_status'] = ['measuring']
                
                elif order.rider_status == 'measuring':
                    transitions['rider_status'] = ['measurement_taken']
                
                elif order.rider_status == 'measurement_taken':
                    # After measurements, rider can mark as delivered
                    transitions['rider_status'] = ['delivered']
        
        elif user_role == OrderStatusTransitionService.ROLE_USER:
            # Customer can mark walk-in measurements as collected
            if order.service_mode == 'walk_in' and order.status == 'ready_for_pickup':
                transitions['status'] = ['collected']
        
        return transitions
    
    @staticmethod
    def _get_fabric_with_stitching_transitions(order, user_role):
        """Get transitions for fabric_with_stitching orders"""
        transitions = {'status': [], 'rider_status': [], 'tailor_status': []}
        
        if user_role == OrderStatusTransitionService.ROLE_ADMIN:
            # Admin can do everything
            transitions['status'] = ['confirmed', 'in_progress', 'ready_for_delivery', 'delivered', 'cancelled']
            transitions['rider_status'] = ['accepted', 'on_way_to_measurement', 'measuring', 'measurement_taken', 
                                           'on_way_to_pickup', 'picked_up', 'on_way_to_delivery', 'delivered']
            transitions['tailor_status'] = ['accepted', 'in_progress', 'stitching_started', 'stitched']
        elif user_role == OrderStatusTransitionService.ROLE_TAILOR:
            # Require rider to accept before tailor can progress (except initial accept)
            if order.rider_status == 'none':
                if order.tailor_status == 'none':
                    # Tailor can only accept the order; no status change yet
                    transitions['tailor_status'] = ['accepted']
                # If tailor has already accepted but rider hasn't, tailor must wait
                return transitions

            if order.status == 'pending':
                # If stitching is complete, order is ready for delivery
                if order.tailor_status == 'stitched':
                    transitions['status'] = ['ready_for_delivery']
                # If stitching has started, allow finishing stitching
                elif order.tailor_status == 'stitching_started':
                    transitions['tailor_status'] = ['stitched']
                # If measurements are already taken and complete, tailor can start stitching directly
                elif (order.order_type == 'fabric_with_stitching' and 
                      order.rider_status == 'measurement_taken' and 
                      order.all_items_have_measurements and 
                      order.tailor_status == 'accepted'):
                    transitions['tailor_status'] = ['stitching_started']
                else:
                    # Otherwise, allow status change to confirmed and tailor acceptance
                    # But only if rider has accepted (checked above - if rider_status == 'none', we return early)
                    transitions['status'] = ['confirmed']
                    if order.tailor_status == 'none':
                        transitions['tailor_status'] = ['accepted']
            elif order.status == 'confirmed':
                # Allow tailor to accept if not yet accepted (for orders that progressed without explicit acceptance)
                if order.tailor_status == 'none' and order.rider_status != 'measurement_taken':
                    transitions['tailor_status'] = ['accepted']
                transitions['status'] = ['in_progress']
                
                # For fabric_with_stitching, only allow progression if measurements are complete
                if order.order_type == 'fabric_with_stitching':
                    # Check if measurements are complete
                    measurements_complete = (order.rider_status == 'measurement_taken' and 
                                           order.all_items_have_measurements)
                    
                    if measurements_complete:
                        # Measurements complete - allow progression
                        if order.tailor_status == 'accepted':
                            transitions['tailor_status'] = ['in_progress', 'stitching_started']
                        elif order.tailor_status == 'stitching_started':
                            transitions['tailor_status'] = ['stitched']
                    # If measurements not complete, don't allow any progression
                else:
                    # fabric_only doesn't need measurements - allow normal progression
                    if order.tailor_status == 'accepted':
                        transitions['tailor_status'] = ['in_progress']
            elif order.status == 'in_progress':
                # Allow tailor to accept if not yet accepted and measurements not taken yet
                if order.tailor_status == 'none' and order.rider_status != 'measurement_taken':
                    transitions['tailor_status'] = ['accepted']
                
                # For fabric_with_stitching, only allow progression if measurements are complete
                if order.order_type == 'fabric_with_stitching':
                    # Check if measurements are complete
                    measurements_complete = (order.rider_status == 'measurement_taken' and 
                                           order.all_items_have_measurements)
                    
                    if measurements_complete:
                        # Measurements complete - allow progression
                        if order.tailor_status == 'accepted':
                            transitions['tailor_status'] = ['in_progress', 'stitching_started']
                        elif order.tailor_status == 'in_progress':
                            transitions['tailor_status'] = ['stitching_started']
                        elif order.tailor_status == 'stitching_started':
                            transitions['tailor_status'] = ['stitched']
                        elif order.tailor_status == 'stitched':
                            transitions['status'] = ['ready_for_delivery']
                    # If measurements not complete, don't allow any progression
                else:
                    # fabric_only doesn't need measurements - allow normal progression
                    if order.tailor_status == 'accepted':
                        transitions['tailor_status'] = ['in_progress']
                    elif order.tailor_status == 'stitched':
                        transitions['status'] = ['ready_for_delivery']
            elif order.status == 'ready_for_delivery':
                # Tailor can't change status once ready for delivery
                pass
        elif user_role == OrderStatusTransitionService.ROLE_RIDER:
            # Rider can accept order if tailor has already accepted (tailor_status == 'accepted')
            if order.rider_status == 'none' and order.tailor_status == 'accepted':
                transitions['rider_status'] = ['accepted']
            elif order.rider_status == 'accepted':
                # Check if all items already have measurements (customer provided them during order creation)
                if order.all_items_have_measurements:
                    # Measurements already provided - skip measurement step
                    transitions['rider_status'] = ['measurement_taken']
                else:
                    # Need to take measurements - rider must go to customer location
                    transitions['rider_status'] = ['on_way_to_measurement']
            elif order.rider_status == 'on_way_to_measurement':
                transitions['rider_status'] = ['measuring']
            elif order.rider_status == 'measuring':
                # Can finish measurement if ready
                transitions['rider_status'] = ['measurement_taken']
            elif order.rider_status == 'measurement_taken':
                # Wait for tailor to stitch - rider can't proceed until tailor finishes
                # Also ensure all items have measurements before allowing pickup
                if order.tailor_status == 'stitched' and order.all_items_have_measurements:
                    transitions['rider_status'] = ['on_way_to_pickup']
            elif order.rider_status == 'on_way_to_pickup':
                transitions['rider_status'] = ['picked_up']
            elif order.rider_status == 'picked_up':
                transitions['rider_status'] = ['on_way_to_delivery']
            elif order.rider_status == 'on_way_to_delivery':
                transitions['rider_status'] = ['delivered']
                transitions['status'] = ['delivered']
        elif user_role == OrderStatusTransitionService.ROLE_USER:
            if order.status == 'pending':
                transitions['status'] = ['cancelled']
        
        return transitions

    @staticmethod
    def _get_walk_in_transitions(order, user_role):
        """Get transitions for walk-in orders (no rider involvement)"""
        transitions = {'status': [], 'rider_status': [], 'tailor_status': []}
        
        if user_role == OrderStatusTransitionService.ROLE_ADMIN:
            transitions['status'] = ['confirmed', 'in_progress', 'ready_for_pickup', 'collected', 'cancelled']
            transitions['tailor_status'] = ['accepted', 'in_progress', 'stitching_started', 'stitched']
        
        elif user_role == OrderStatusTransitionService.ROLE_TAILOR:
            # For walk-in orders, tailors strictly update their OWN status (tailor_status)
            # The main status is automatically synced via _sync_main_status() model method
            
            if order.status == 'pending':
                # No direct status update - must accept first
                # transitions['status'] = ['confirmed']  <-- REMOVED to avoid duplicate/error
                if order.tailor_status == 'none':
                    transitions['tailor_status'] = ['accepted']
            
            elif order.status == 'confirmed':
                # No direct status update
                # transitions['status'] = ['in_progress'] <-- REMOVED
                if order.tailor_status == 'accepted':
                    # User requested to skip 'in_progress' and go directly to stitching
                    # BUT only if measurements are present for stitching orders
                    if order.order_type == 'fabric_with_stitching' and not order.all_items_have_measurements:
                        transitions['tailor_status'] = []
                        transitions['custom_actions'] = [{
                            "type": "form_action", 
                            "value": "record_measurements",
                            "label": "Record Measurements",
                            "description": "Open measurement form for customer"
                        }]
                    else:
                        transitions['tailor_status'] = ['stitching_started']
                elif order.tailor_status == 'none':
                    # Allow late acceptance (jump to stitching)
                    transitions['tailor_status'] = ['accepted']
                    # Add stitching_started only if measurements present (or if we want to allow quick accept -> check -> stitch loop)
                    if not (order.order_type == 'fabric_with_stitching' and not order.all_items_have_measurements):
                         transitions['tailor_status'].append('stitching_started')
            
            elif order.status == 'in_progress':
                if order.tailor_status == 'accepted':
                    if order.order_type == 'fabric_with_stitching' and not order.all_items_have_measurements:
                        transitions['tailor_status'] = []
                        transitions['custom_actions'] = [{
                            "type": "form_action", 
                            "value": "record_measurements",
                            "label": "Record Measurements",
                            "description": "Open measurement form for customer"
                        }]
                    else:
                        transitions['tailor_status'] = ['stitching_started']
                elif order.tailor_status == 'in_progress':
                    if order.order_type == 'fabric_with_stitching' and not order.all_items_have_measurements:
                        transitions['tailor_status'] = []
                        transitions['custom_actions'] = [{
                            "type": "form_action", 
                            "value": "record_measurements",
                            "label": "Record Measurements",
                            "description": "Open measurement form for customer"
                        }]
                    else:
                        transitions['tailor_status'] = ['stitching_started']
                elif order.tailor_status == 'stitching_started':
                    transitions['tailor_status'] = ['stitched']
                # When tailor_status='stitched', _sync_main_status() will auto-transition
                # the main status from 'in_progress' to 'ready_for_pickup'
                # No explicit tailor_status transitions needed at this point
            
            elif order.status == 'ready_for_pickup':
                # Tailor's work is done - waiting for customer to collect
                # Only customer can mark as collected
                pass
        
        elif user_role == OrderStatusTransitionService.ROLE_USER:
            if order.status == 'pending':
                transitions['status'] = ['cancelled']
            elif order.status == 'ready_for_pickup':
                # Customer can mark as collected
                transitions['status'] = ['collected']
        
        return transitions
    
    @staticmethod
    def validate_transition(order, new_status=None, new_rider_status=None, new_tailor_status=None, user_role=None, user=None):
        """
        Validate if a status transition is allowed.
        
        Args:
            order: Order instance
            new_status: New main status (optional)
            new_rider_status: New rider status (optional)
            new_tailor_status: New tailor status (optional)
            user_role: Role of the user making the change
            user: User instance (for additional validation)
        
        Returns:
            tuple: (is_valid: bool, error_message: str)
        """
        # Check if order is in final state
        if order.status in ['delivered', 'cancelled', 'collected']:
            return False, f"Cannot change status of {order.status} order"
        
        # Role-based access checks
        if user_role == OrderStatusTransitionService.ROLE_TAILOR:
            if order.tailor != user:
                return False, "You can only update orders assigned to you"
        elif user_role == OrderStatusTransitionService.ROLE_RIDER:
            if order.rider != user:
                return False, "You can only update orders assigned to you"
        elif user_role == OrderStatusTransitionService.ROLE_USER:
            if order.customer != user:
                return False, "You can only update your own orders"
            # Users can only cancel pending orders or mark walk-ins as collected
            if new_status and new_status not in ['cancelled', 'collected']:
                return False, "Customers can only cancel orders or mark them as collected"
            if new_status == 'cancelled' and order.status != 'pending':
                return False, "Orders can only be cancelled when status is pending"
        
        # Get allowed transitions
        allowed = OrderStatusTransitionService.get_allowed_transitions(order, user_role)
        
        # Validate main status
        if new_status and new_status != order.status:
            if new_status not in allowed['status']:
                return False, f"Cannot change status from {order.status} to {new_status}. Allowed: {allowed['status']}"
        
        # Validate rider status
        if new_rider_status and new_rider_status != order.rider_status:
            if new_rider_status not in allowed['rider_status']:
                return False, f"Cannot change rider_status from {order.rider_status} to {new_rider_status}. Allowed: {allowed['rider_status']}"
        
        # Validate tailor status
        if new_tailor_status and new_tailor_status != order.tailor_status:
            if new_tailor_status not in allowed['tailor_status']:
                return False, f"Cannot change tailor_status from {order.tailor_status} to {new_tailor_status}. Allowed: {allowed['tailor_status']}"
        
        # Additional business logic validations
        if new_status == 'cancelled' and user_role != OrderStatusTransitionService.ROLE_USER and user_role != OrderStatusTransitionService.ROLE_ADMIN:
            return False, "Only customers and admins can cancel orders"
            
        # Validate measurement completion before starting stitching
        if new_tailor_status == 'stitching_started' and not order.all_items_have_measurements:
            return False, "Cannot start stitching. Please ensure all items have measurements recorded."
            
        # Validate measurement completion for rider (Home Delivery flow)
        if new_rider_status == 'measurement_taken' and not order.all_items_have_measurements:
            return False, "Cannot complete measurement step. Please ensure all items have measurements recorded."
        
        # Validate stitching completion date is set before starting stitching
        if new_tailor_status == 'stitching_started':
            if order.order_type == 'fabric_with_stitching' and not order.stitching_completion_date:
                return False, "You must set the stitching completion date before starting stitching. Please update the order with expected completion date first."
        
        return True, ""
    
    @staticmethod
    def transition(order, new_status=None, new_rider_status=None, new_tailor_status=None, 
                   user_role=None, user=None, notes=None):
        """
        Perform a status transition with validation and history tracking.
        
        Args:
            order: Order instance
            new_status: New main status (optional)
            new_rider_status: New rider status (optional)
            new_tailor_status: New tailor status (optional)
            user_role: Role of the user making the change
            user: User instance
            notes: Optional notes about the transition
        
        Returns:
            tuple: (success: bool, error_message: str, updated_order: Order)
        """
        # Validate transition
        is_valid, error_msg = OrderStatusTransitionService.validate_transition(
            order, new_status, new_rider_status, new_tailor_status, user_role, user
        )
        
        if not is_valid:
            return False, error_msg, order
        
        # Store old values for history
        old_status = order.status
        old_rider_status = order.rider_status
        old_tailor_status = order.tailor_status
        
        # Update statuses
        if new_status:
            order.status = new_status
        if new_rider_status:
            order.rider_status = new_rider_status
        if new_tailor_status:
            order.tailor_status = new_tailor_status
        
        # Auto-sync main status based on activity statuses
        OrderStatusTransitionService._sync_main_status(order)
        
        # Determine what actually changed (after sync, to capture auto-sync changes)
        status_changed = order.status != old_status
        rider_status_changed = new_rider_status and new_rider_status != old_rider_status
        tailor_status_changed = new_tailor_status and new_tailor_status != old_tailor_status
        
        # Save order
        order.save()
        
        # Create history entry if anything changed
        if status_changed or rider_status_changed or tailor_status_changed:
            from apps.orders.models import OrderStatusHistory
            OrderStatusHistory.objects.create(
                order=order,
                status=order.status,
                previous_status=old_status,
                changed_by=user,
                notes=notes or f"Status: {old_status}→{order.status}, "
                              f"Rider: {old_rider_status}→{order.rider_status}, "
                              f"Tailor: {old_tailor_status}→{order.tailor_status}"
            )
        
        return True, "Status updated successfully", order
    
    @staticmethod
    def _sync_main_status(order):
        """
        Automatically sync main status based on rider_status and tailor_status.
        This ensures the main status reflects the current state of the order.
        """
        # If collected (Walk-In final state)
        if order.status == 'collected':
            return

        # If delivered by rider, main status should be delivered
        if order.rider_status == 'delivered':
            order.status = 'delivered'
            return
        
        # If cancelled, keep cancelled
        if order.status == 'cancelled':
            return

        # NEW: For Walk-In flow
        if order.service_mode == 'walk_in':
            if order.status == 'pending':
                if order.tailor_status != 'none':
                    order.status = 'confirmed'
                else:
                    return
            elif order.status == 'confirmed' and order.tailor_status in ['in_progress', 'stitching_started']:
                 order.status = 'in_progress'
            elif order.tailor_status == 'stitched' and order.status != 'collected':
                order.status = 'ready_for_pickup'
            elif order.tailor_status == 'measurements_complete' and order.status != 'collected':
                # For measurement service walk-in orders - measurements are done, ready for pickup
                order.status = 'ready_for_pickup'
            return

        # For measurement_service flow (Home Delivery)
        if order.order_type == 'measurement_service':
            if order.service_mode == 'home_delivery':
                # Home delivery measurement: rider-driven flow (no tailor confirmation needed)
                if order.status == 'pending' and order.rider_status == 'accepted':
                    order.status = 'confirmed'
                elif order.status == 'confirmed' and order.rider_status in ['on_way_to_measurement', 'measuring']:
                    order.status = 'in_progress'
                elif order.rider_status == 'delivered':
                    order.status = 'delivered'
            # Walk-in measurement handled in walk_in flow above
            return

        # For fabric_only flow (Home Delivery)
        if order.order_type == 'fabric_only':
            if order.status == 'pending':
                if order.tailor_status != 'none':
                    order.status = 'confirmed'
                else:
                    return
            elif order.status == 'confirmed' and order.rider_status in ['accepted', 'on_way_to_pickup', 'picked_up', 'on_way_to_delivery']:
                order.status = 'in_progress'
            elif order.rider_status == 'picked_up' and order.status == 'in_progress':
                order.status = 'ready_for_delivery'
        
        # For fabric_with_stitching flow (Home Delivery)
        else:  # fabric_with_stitching
            if order.status == 'pending':
                if order.tailor_status != 'none':
                    order.status = 'confirmed'
                else:
                    return
            elif order.status == 'confirmed' and order.rider_status in ['accepted', 'on_way_to_measurement', 'measurement_taken']:
                order.status = 'in_progress'
            elif order.tailor_status == 'stitched' and order.rider_status in ['on_way_to_pickup', 'picked_up', 'on_way_to_delivery']:
                order.status = 'ready_for_delivery'





