#!/usr/bin/env python
"""Quick test for free delivery threshold"""
import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zthob.settings')
django.setup()

from decimal import Decimal
from apps.core.models import SystemSettings
from apps.orders.services import OrderCalculationService
from apps.tailors.models import TailorProfile, Fabric

def test_free_delivery():
    """Test free delivery threshold"""
    print("\n=== Testing Free Delivery Threshold ===")
    
    tailor_profile = TailorProfile.objects.first()
    if not tailor_profile:
        print("⚠ No tailor profile found")
        return
    
    fabric = Fabric.objects.filter(tailor=tailor_profile, is_active=True).first()
    if not fabric:
        print("⚠ No fabric found")
        return
    
    settings = SystemSettings.get_active_settings()
    print(f"Free delivery threshold: {settings.free_delivery_threshold} SAR")
    
    # Test with subtotal below threshold
    items_below = [{'fabric': fabric, 'quantity': 1}]
    totals_below = OrderCalculationService.calculate_all_totals(items_data=items_below)
    print(f"\nSubtotal below threshold ({totals_below['subtotal']} < {settings.free_delivery_threshold}):")
    print(f"  Delivery fee: {totals_below['delivery_fee']} SAR")
    
    # Test with high quantity to exceed threshold
    if fabric.price > 0:
        quantity_needed = int(settings.free_delivery_threshold / fabric.price) + 1
        items_above = [{'fabric': fabric, 'quantity': quantity_needed}]
        totals_above = OrderCalculationService.calculate_all_totals(items_data=items_above)
        print(f"\nSubtotal above threshold ({totals_above['subtotal']} >= {settings.free_delivery_threshold}):")
        print(f"  Delivery fee: {totals_above['delivery_fee']} SAR (should be 0.00)")
        
        if totals_above['delivery_fee'] == Decimal('0.00'):
            print("✓ Free delivery threshold working correctly!")
        else:
            print(f"✗ Expected 0.00, got {totals_above['delivery_fee']}")

if __name__ == '__main__':
    test_free_delivery()

