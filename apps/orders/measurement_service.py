from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from apps.customers.models import FamilyMember


class MeasurementCompletionService:
    """
    Service for completing measurement orders.
    Saves measurements from OrderItems to customer/family member profiles.
    """
    
    @staticmethod
    def complete_measurement_order(order):
        """
        Save measurements from order items to customer/family member profiles.
        Mark account as used if this is a free measurement order.
        
        Args:
            order: Order instance
        
        Returns:
            tuple: (success: bool, message: str)
        """
        if order.order_type != 'measurement_service':
            return False, "Not a measurement service order"
        
        # Get all items (each item represents a person to measure)
        items = order.order_items.all()
        
        if not items.exists():
            return False, "No measurement recipients found"
        
        # Check if all items have measurements
        incomplete_items = [
            item for item in items 
            if not item.measurements or len(item.measurements) == 0
        ]
        
        if incomplete_items:
            return False, f"{len(incomplete_items)} people still need measurements"
        
        # Save measurements to profiles
        with transaction.atomic():
            for item in items:
                if item.family_member is None:
                    # Save to customer profile
                    profile = order.customer.customer_profile
                    profile.measurements = item.measurements
                    profile.save()
                else:
                    # Save to family member
                    family_member = item.family_member
                    family_member.measurements = item.measurements
                    family_member.save()
            
            # Mark account as used if this is a free measurement order
            if order.is_free_measurement:
                profile = order.customer.customer_profile
                profile.first_free_measurement_used = True
                profile.free_measurement_date = timezone.now()
                profile.save()
        
        return True, "Measurements saved successfully"
    
    @staticmethod
    def get_measurement_completion_status(order):
        """
        Get completion status for a measurement order.
        
        Returns:
            dict: {
                'total_recipients': int,
                'completed': int,
                'pending': int,
                'is_complete': bool
            }
        """
        if order.order_type != 'measurement_service':
            return None
        
        items = order.order_items.all()
        total = items.count()
        completed = sum(1 for item in items if item.measurements and len(item.measurements) > 0)
        
        return {
            'total_recipients': total,
            'completed': completed,
            'pending': total - completed,
            'is_complete': completed == total and total > 0
        }
