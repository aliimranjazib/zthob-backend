from decimal import Decimal
from django.db import transaction
from django.conf import settings
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
    def calculate_all_totals(items_data, distance_km=None, delivery_address=None, tailor=None, tax_rate=None):
        """
        Calculate all order totals.
        
        Args:
            items_data: List of items with fabric and quantity
            distance_km: Distance in kilometers for delivery fee calculation
            delivery_address: Delivery address (optional)
            tailor: Tailor object (optional)
            tax_rate: Custom tax rate (optional, uses system settings if not provided)
        """
        subtotal = OrderCalculationService.calculate_subtotal(items_data)
        tax_amount = OrderCalculationService.calculate_tax(subtotal, tax_rate)
        delivery_fee = OrderCalculationService.calculate_delivery_fee(
            subtotal, 
            distance_km=distance_km,
            delivery_address=delivery_address,
            tailor=tailor
        )
        total_amount = subtotal + tax_amount + delivery_fee
        
        return {
            'subtotal': subtotal,
            'tax_amount': tax_amount,
            'delivery_fee': delivery_fee,
            'total_amount': total_amount.quantize(Decimal('0.01'))
        }





