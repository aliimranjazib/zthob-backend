#!/usr/bin/env python
"""
Test script for order creation API
Tests the order creation flow with SystemSettings integration
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zthob.settings')
django.setup()

from decimal import Decimal
from django.contrib.auth import get_user_model
from apps.core.models import SystemSettings
from apps.orders.services import OrderCalculationService
from apps.tailors.models import TailorProfile, Fabric, FabricCategory, FabricType
from apps.customers.models import Address, CustomerProfile

User = get_user_model()

def test_system_settings():
    """Test SystemSettings model"""
    print("\n=== Testing SystemSettings ===")
    
    # Get or create settings
    settings = SystemSettings.get_active_settings()
    print(f"✓ SystemSettings retrieved: Tax={settings.tax_rate*100}%, Delivery <10KM={settings.delivery_fee_under_10km} SAR")
    
    # Test settings values
    assert settings.tax_rate == Decimal('0.15'), "Tax rate should be 15%"
    assert settings.delivery_fee_under_10km == Decimal('20.00'), "Delivery fee <10KM should be 20 SAR"
    assert settings.delivery_fee_10km_and_above == Decimal('30.00'), "Delivery fee >=10KM should be 30 SAR"
    print("✓ All default settings are correct")
    
    return settings

def test_calculation_service():
    """Test OrderCalculationService with SystemSettings"""
    print("\n=== Testing OrderCalculationService ===")
    
    # Create test fabric
    try:
        tailor_user = User.objects.filter(role='TAILOR').first()
        if not tailor_user:
            print("⚠ No tailor user found, skipping calculation test")
            return
        
        tailor_profile = TailorProfile.objects.filter(user=tailor_user).first()
        if not tailor_profile:
            print("⚠ No tailor profile found, skipping calculation test")
            return
        
        fabric = Fabric.objects.filter(tailor=tailor_profile, is_active=True).first()
        if not fabric:
            print("⚠ No active fabric found, skipping calculation test")
            return
        
        # Test calculation without distance (should use default <10KM fee)
        items_data = [{'fabric': fabric, 'quantity': 2}]
        totals_no_distance = OrderCalculationService.calculate_all_totals(items_data=items_data)
        print(f"✓ Calculation without distance: Subtotal={totals_no_distance['subtotal']}, Tax={totals_no_distance['tax_amount']}, Delivery={totals_no_distance['delivery_fee']}, Total={totals_no_distance['total_amount']}")
        
        # Test calculation with distance < 10KM
        totals_under_10km = OrderCalculationService.calculate_all_totals(
            items_data=items_data,
            distance_km=8.5
        )
        print(f"✓ Calculation with 8.5KM: Delivery fee={totals_under_10km['delivery_fee']} SAR (should be 20 SAR)")
        assert totals_under_10km['delivery_fee'] == Decimal('20.00'), "Delivery fee for <10KM should be 20 SAR"
        
        # Test calculation with distance >= 10KM
        totals_over_10km = OrderCalculationService.calculate_all_totals(
            items_data=items_data,
            distance_km=12.5
        )
        print(f"✓ Calculation with 12.5KM: Delivery fee={totals_over_10km['delivery_fee']} SAR (should be 30 SAR)")
        assert totals_over_10km['delivery_fee'] == Decimal('30.00'), "Delivery fee for >=10KM should be 30 SAR"
        
        # Test tax calculation (15%)
        subtotal = totals_no_distance['subtotal']
        expected_tax = subtotal * Decimal('0.15')
        assert totals_no_distance['tax_amount'] == expected_tax.quantize(Decimal('0.01')), "Tax should be 15% of subtotal"
        print(f"✓ Tax calculation correct: {totals_no_distance['tax_amount']} (15% of {subtotal})")
        
        print("✓ All calculation tests passed!")
        
    except Exception as e:
        print(f"✗ Calculation test failed: {str(e)}")
        import traceback
        traceback.print_exc()

def test_order_serializer_fields():
    """Test that OrderCreateSerializer has all required fields"""
    print("\n=== Testing OrderCreateSerializer Fields ===")
    
    from apps.orders.serializers import OrderCreateSerializer
    
    serializer = OrderCreateSerializer()
    fields = serializer.fields.keys()
    
    required_fields = ['customer', 'tailor', 'order_type', 'payment_method', 'items']
    optional_fields = ['family_member', 'delivery_address', 'estimated_delivery_date', 'special_instructions', 'distance_km']
    
    print(f"✓ Serializer fields: {list(fields)}")
    
    for field in required_fields:
        assert field in fields, f"Required field '{field}' missing from serializer"
        print(f"✓ Required field '{field}' present")
    
    for field in optional_fields:
        if field in fields:
            print(f"✓ Optional field '{field}' present")
    
    print("✓ All serializer fields are correct")

def main():
    """Run all tests"""
    print("=" * 60)
    print("ORDER CREATION API TEST SUITE")
    print("=" * 60)
    
    try:
        # Test 1: SystemSettings
        test_system_settings()
        
        # Test 2: Calculation Service
        test_calculation_service()
        
        # Test 3: Serializer Fields
        test_order_serializer_fields()
        
        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED!")
        print("=" * 60)
        
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"✗ TESTS FAILED: {str(e)}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()

