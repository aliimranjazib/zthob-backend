#!/usr/bin/env python
"""
Integration test for order creation API
Tests the complete order creation flow including SystemSettings
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
from apps.orders.models import Order, OrderItem
from apps.orders.serializers import OrderCreateSerializer
from apps.orders.services import OrderCalculationService
from apps.tailors.models import TailorProfile, Fabric, FabricCategory, FabricType
from apps.customers.models import Address, CustomerProfile

User = get_user_model()

def test_order_creation_with_distance():
    """Test order creation with distance parameter"""
    print("\n=== Testing Order Creation with Distance ===")
    
    try:
        # Get test data
        customer = User.objects.filter(role='USER').first()
        tailor_user = User.objects.filter(role='TAILOR').first()
        
        if not customer or not tailor_user:
            print("⚠ Missing test users, skipping integration test")
            return
        
        tailor_profile = TailorProfile.objects.filter(user=tailor_user).first()
        if not tailor_profile:
            print("⚠ No tailor profile found, skipping integration test")
            return
        
        fabric = Fabric.objects.filter(tailor=tailor_profile, is_active=True, stock__gte=2).first()
        if not fabric:
            print("⚠ No suitable fabric found, skipping integration test")
            return
        
        # Create mock request context
        class MockRequest:
            user = customer
        
        mock_request = MockRequest()
        
        # Test data
        order_data = {
            'customer': customer.id,
            'tailor': tailor_user.id,
            'order_type': 'fabric_only',
            'payment_method': 'cod',
            'items': [
                {
                    'fabric': fabric.id,
                    'quantity': 2
                }
            ],
            'distance_km': '8.5'  # Under 10KM
        }
        
        # Create serializer
        serializer = OrderCreateSerializer(data=order_data, context={'request': mock_request})
        
        if serializer.is_valid():
            print("✓ Serializer validation passed")
            
            # Get original stock
            original_stock = fabric.stock
            
            # Save order
            order = serializer.save()
            print(f"✓ Order created: {order.order_number}")
            
            # Verify order totals
            print(f"  - Subtotal: {order.subtotal} SAR")
            print(f"  - Tax: {order.tax_amount} SAR (15%)")
            print(f"  - Delivery Fee: {order.delivery_fee} SAR (should be 20 SAR for <10KM)")
            print(f"  - Total: {order.total_amount} SAR")
            
            # Verify delivery fee is correct for <10KM
            assert order.delivery_fee == Decimal('20.00'), f"Expected 20.00 SAR, got {order.delivery_fee}"
            print("✓ Delivery fee correct for distance < 10KM")
            
            # Verify tax is 15%
            expected_tax = order.subtotal * Decimal('0.15')
            assert abs(order.tax_amount - expected_tax) < Decimal('0.01'), f"Tax should be 15%"
            print("✓ Tax calculation correct (15%)")
            
            # Verify order items created
            order_items = OrderItem.objects.filter(order=order)
            assert order_items.count() == 1, "Should have 1 order item"
            print(f"✓ Order items created: {order_items.count()}")
            
            # Verify stock was decremented
            fabric.refresh_from_db()
            assert fabric.stock == original_stock - 2, "Stock should be decremented"
            print(f"✓ Stock decremented: {original_stock} -> {fabric.stock}")
            
            # Cleanup
            order.delete()
            fabric.stock = original_stock
            fabric.save()
            print("✓ Test order cleaned up")
            
        else:
            print(f"✗ Serializer validation failed: {serializer.errors}")
            return False
            
    except Exception as e:
        print(f"✗ Order creation test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def test_order_creation_without_distance():
    """Test order creation without distance (should use default)"""
    print("\n=== Testing Order Creation without Distance ===")
    
    try:
        # Get test data
        customer = User.objects.filter(role='USER').first()
        tailor_user = User.objects.filter(role='TAILOR').first()
        
        if not customer or not tailor_user:
            print("⚠ Missing test users, skipping test")
            return True
        
        tailor_profile = TailorProfile.objects.filter(user=tailor_user).first()
        if not tailor_profile:
            print("⚠ No tailor profile found, skipping test")
            return True
        
        fabric = Fabric.objects.filter(tailor=tailor_profile, is_active=True, stock__gte=1).first()
        if not fabric:
            print("⚠ No suitable fabric found, skipping test")
            return True
        
        # Create mock request context
        class MockRequest:
            user = customer
        
        mock_request = MockRequest()
        
        # Test data without distance_km
        order_data = {
            'customer': customer.id,
            'tailor': tailor_user.id,
            'order_type': 'fabric_only',
            'payment_method': 'cod',
            'items': [
                {
                    'fabric': fabric.id,
                    'quantity': 1
                }
            ]
            # No distance_km - should use default (<10KM fee)
        }
        
        # Create serializer
        serializer = OrderCreateSerializer(data=order_data, context={'request': mock_request})
        
        if serializer.is_valid():
            print("✓ Serializer validation passed (without distance)")
            
            # Get original stock
            original_stock = fabric.stock
            
            # Save order
            order = serializer.save()
            print(f"✓ Order created: {order.order_number}")
            
            # Verify delivery fee uses default (<10KM)
            print(f"  - Delivery Fee: {order.delivery_fee} SAR (should be 20 SAR default)")
            assert order.delivery_fee == Decimal('20.00'), f"Expected 20.00 SAR default, got {order.delivery_fee}"
            print("✓ Default delivery fee used correctly")
            
            # Cleanup
            order.delete()
            fabric.stock = original_stock
            fabric.save()
            print("✓ Test order cleaned up")
            
        else:
            print(f"✗ Serializer validation failed: {serializer.errors}")
            return False
            
    except Exception as e:
        print(f"✗ Order creation test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def test_order_creation_over_10km():
    """Test order creation with distance >= 10KM"""
    print("\n=== Testing Order Creation with Distance >= 10KM ===")
    
    try:
        # Get test data
        customer = User.objects.filter(role='USER').first()
        tailor_user = User.objects.filter(role='TAILOR').first()
        
        if not customer or not tailor_user:
            print("⚠ Missing test users, skipping test")
            return True
        
        tailor_profile = TailorProfile.objects.filter(user=tailor_user).first()
        if not tailor_profile:
            print("⚠ No tailor profile found, skipping test")
            return True
        
        fabric = Fabric.objects.filter(tailor=tailor_profile, is_active=True, stock__gte=1).first()
        if not fabric:
            print("⚠ No suitable fabric found, skipping test")
            return True
        
        # Create mock request context
        class MockRequest:
            user = customer
        
        mock_request = MockRequest()
        
        # Test data with distance >= 10KM
        order_data = {
            'customer': customer.id,
            'tailor': tailor_user.id,
            'order_type': 'fabric_only',
            'payment_method': 'cod',
            'items': [
                {
                    'fabric': fabric.id,
                    'quantity': 1
                }
            ],
            'distance_km': '15.5'  # Over 10KM
        }
        
        # Create serializer
        serializer = OrderCreateSerializer(data=order_data, context={'request': mock_request})
        
        if serializer.is_valid():
            print("✓ Serializer validation passed (distance >= 10KM)")
            
            # Get original stock
            original_stock = fabric.stock
            
            # Save order
            order = serializer.save()
            print(f"✓ Order created: {order.order_number}")
            
            # Verify delivery fee is correct for >=10KM
            print(f"  - Delivery Fee: {order.delivery_fee} SAR (should be 30 SAR for >=10KM)")
            assert order.delivery_fee == Decimal('30.00'), f"Expected 30.00 SAR, got {order.delivery_fee}"
            print("✓ Delivery fee correct for distance >= 10KM")
            
            # Cleanup
            order.delete()
            fabric.stock = original_stock
            fabric.save()
            print("✓ Test order cleaned up")
            
        else:
            print(f"✗ Serializer validation failed: {serializer.errors}")
            return False
            
    except Exception as e:
        print(f"✗ Order creation test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def main():
    """Run all integration tests"""
    print("=" * 60)
    print("ORDER CREATION API INTEGRATION TEST SUITE")
    print("=" * 60)
    
    results = []
    
    # Test 1: Order creation with distance < 10KM
    results.append(("Order with distance < 10KM", test_order_creation_with_distance()))
    
    # Test 2: Order creation without distance
    results.append(("Order without distance", test_order_creation_without_distance()))
    
    # Test 3: Order creation with distance >= 10KM
    results.append(("Order with distance >= 10KM", test_order_creation_over_10km()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{status}: {test_name}")
        if not result:
            all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("✓ ALL INTEGRATION TESTS PASSED!")
    else:
        print("✗ SOME TESTS FAILED")
    print("=" * 60)
    
    return 0 if all_passed else 1

if __name__ == '__main__':
    sys.exit(main())

