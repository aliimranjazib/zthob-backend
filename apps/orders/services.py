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
    def calculate_delivery_fee(subtotal, distance_km=None, delivery_address=None, tailor=None):
        """
        Calculate delivery fee based on distance and order subtotal.
        
        Args:
            subtotal: Order subtotal amount
            distance_km: Distance in kilometers (required for distance-based calculation)
            delivery_address: Delivery address (optional, for future use)
            tailor: Tailor object (optional, for future use)
        """
        system_settings = OrderCalculationService.get_system_settings()
        
        # Check for free delivery threshold
        if system_settings.free_delivery_threshold > 0:
            if subtotal >= system_settings.free_delivery_threshold:
                return Decimal('0.00')
        
        # Calculate based on distance if provided
        if distance_km is not None:
            if distance_km < system_settings.distance_threshold_km:
                return system_settings.delivery_fee_under_10km
            else:
                return system_settings.delivery_fee_10km_and_above
        
        # Fallback to default (under 10km fee) if distance not provided
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
    def calculate_all_totals(items_data, distance_km=None, delivery_address=None, tailor=None, tax_rate=None, order_type='fabric_only'):
        """
        Calculate all order totals.
        
        Args:
            items_data: List of items with fabric and quantity
            distance_km: Distance in kilometers for delivery fee calculation
            delivery_address: Delivery address (optional)
            tailor: Tailor object (optional)
            tax_rate: Custom tax rate (optional, uses system settings if not provided)
            order_type: Type of order ('fabric_only' or 'fabric_with_stitching') - determines if stitching price is included
        """
        subtotal = OrderCalculationService.calculate_subtotal(items_data)
        
        # Calculate stitching price if order type is fabric_with_stitching
        stitching_price = OrderCalculationService.calculate_stitching_price(items_data, order_type)
        
        # Subtotal includes fabric price, stitching price is added separately
        # Tax is calculated on subtotal (fabric price only)
        tax_amount = OrderCalculationService.calculate_tax(subtotal, tax_rate)
        
        # Delivery fee is calculated on subtotal (fabric price only)
        delivery_fee = OrderCalculationService.calculate_delivery_fee(
            subtotal, 
            distance_km=distance_km,
            delivery_address=delivery_address,
            tailor=tailor
        )
        
        # Total includes: subtotal (fabric) + stitching_price + tax + delivery_fee
        total_amount = subtotal + stitching_price + tax_amount + delivery_fee
        
        return {
            'subtotal': subtotal,
            'stitching_price': stitching_price,
            'tax_amount': tax_amount,
            'delivery_fee': delivery_fee,
            'total_amount': total_amount.quantize(Decimal('0.01'))
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
        
        if order.order_type == 'fabric_only':
            return OrderStatusTransitionService._get_fabric_only_transitions(order, user_role)
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
            if order.status == 'pending':
                transitions['status'] = ['confirmed']
                transitions['tailor_status'] = ['accepted']
            elif order.status == 'confirmed':
                transitions['status'] = ['in_progress']
            elif order.status == 'in_progress':
                transitions['status'] = ['ready_for_delivery']
            elif order.status == 'ready_for_delivery':
                # Tailor can't change status once ready for delivery
                pass
        elif user_role == OrderStatusTransitionService.ROLE_RIDER:
            # Rider can accept order if status is confirmed, in_progress, or ready_for_delivery
            if order.rider_status == 'none' and order.status in ['confirmed', 'in_progress', 'ready_for_delivery']:
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
    def _get_fabric_with_stitching_transitions(order, user_role):
        """Get transitions for fabric_with_stitching orders"""
        transitions = {'status': [], 'rider_status': [], 'tailor_status': []}
        
        if user_role == OrderStatusTransitionService.ROLE_ADMIN:
            # Admin can do everything
            transitions['status'] = ['confirmed', 'in_progress', 'ready_for_delivery', 'delivered', 'cancelled']
            transitions['rider_status'] = ['accepted', 'on_way_to_measurement', 'measurement_taken', 
                                           'on_way_to_pickup', 'picked_up', 'on_way_to_delivery', 'delivered']
            transitions['tailor_status'] = ['accepted', 'stitching_started', 'stitched']
        elif user_role == OrderStatusTransitionService.ROLE_TAILOR:
            if order.status == 'pending':
                transitions['status'] = ['confirmed']
                transitions['tailor_status'] = ['accepted']
            elif order.status == 'confirmed':
                transitions['status'] = ['in_progress']
            elif order.status == 'in_progress':
                if order.rider_status == 'measurement_taken' and order.tailor_status == 'accepted':
                    transitions['tailor_status'] = ['stitching_started']
                elif order.tailor_status == 'stitching_started':
                    transitions['tailor_status'] = ['stitched']
                elif order.tailor_status == 'stitched':
                    transitions['status'] = ['ready_for_delivery']
            elif order.status == 'ready_for_delivery':
                # Tailor can't change status once ready for delivery
                pass
        elif user_role == OrderStatusTransitionService.ROLE_RIDER:
            # Rider can accept order if status is confirmed, in_progress, or ready_for_delivery
            if order.rider_status == 'none' and order.status in ['confirmed', 'in_progress', 'ready_for_delivery']:
                transitions['rider_status'] = ['accepted']
            elif order.rider_status == 'accepted':
                transitions['rider_status'] = ['on_way_to_measurement']
            elif order.rider_status == 'on_way_to_measurement':
                transitions['rider_status'] = ['measurement_taken']
            elif order.rider_status == 'measurement_taken':
                # Wait for tailor to stitch - rider can't proceed until tailor finishes
                if order.tailor_status == 'stitched':
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
        if order.status in ['delivered', 'cancelled']:
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
            # Users can only cancel pending orders
            if new_status and new_status != 'cancelled':
                return False, "Customers can only cancel orders"
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
        # If delivered by rider, main status should be delivered
        if order.rider_status == 'delivered':
            order.status = 'delivered'
            return
        
        # If cancelled, keep cancelled
        if order.status == 'cancelled':
            return
        
        # For fabric_only flow
        if order.order_type == 'fabric_only':
            if order.status == 'pending':
                return  # Don't auto-change from pending
            elif order.status == 'confirmed' and order.rider_status in ['accepted', 'on_way_to_pickup', 'picked_up', 'on_way_to_delivery']:
                order.status = 'in_progress'
            elif order.rider_status == 'picked_up' and order.status == 'in_progress':
                order.status = 'ready_for_delivery'
        
        # For fabric_with_stitching flow
        else:  # fabric_with_stitching
            if order.status == 'pending':
                return  # Don't auto-change from pending
            elif order.status == 'confirmed' and order.rider_status in ['accepted', 'on_way_to_measurement', 'measurement_taken']:
                order.status = 'in_progress'
            elif order.tailor_status == 'stitched' and order.rider_status in ['on_way_to_pickup', 'picked_up', 'on_way_to_delivery']:
                order.status = 'ready_for_delivery'





