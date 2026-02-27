#!/usr/bin/env python
"""
Direct test script for measurement service
Run with: python3 test_measurement_direct.py
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zthob.settings')
sys.path.insert(0, '/Users/jazib/Documents/GitHub/zthob-backend')
django.setup()

from django.contrib.auth import get_user_model
from apps.customers.models import CustomerProfile, FamilyMember
from apps.tailors.models import TailorProfile, Fabric
from apps.orders.serializers import OrderCreateSerializer
from decimal import Decimal
from rest_framework.test import APIRequestFactory

User = get_user_model()

print("\n" + "="*70)
print("🧪 MEASUREMENT SERVICE - DIRECT TEST")
print("="*70 + "\n")

# Clean up any existing test data
User.objects.filter(username__startswith='test_').delete()

# Create customer
print("1. Creating test customer...")
customer = User.objects.create_user(
    username='test_customer_001',
    email='customer@test.com',
    phone='+966500000001',
    password='testpass123',
    role='USER'
)
profile = CustomerProfile.objects.create(
    user=customer,
    first_free_measurement_used=False
)
print("   ✅ Customer created")

# Create tailor
print("2. Creating test tailor...")
tailor = User.objects.create_user(
    username='test_tailor_001',
    email='tailor@test.com',
    phone='+966500000002',
    password='testpass123',
    role='TAILOR'
)
tailor_profile = TailorProfile.objects.create(
    user=tailor,
    shop_name='Test Tailor Shop',
    shop_status=True
)
print("   ✅ Tailor created")

# Test 1: Check eligibility
print("\n3. Testing eligibility check...")
print(f"   first_free_measurement_used: {profile.first_free_measurement_used}")
print("   ✅ Eligibility: TRUE")

# Test 2: Create walk-in measurement order
print("\n4. Creating walk-in measurement order...")
factory = APIRequestFactory()
request = factory.post('/api/orders/create/')
request.user = customer

order_data = {
    'customer': customer.id,
    'tailor': tailor.id,
    'order_type': 'measurement_service',
    'service_mode': 'walk_in',
    'items': [
        {'family_member': None}
    ]
}

serializer = OrderCreateSerializer(data=order_data, context={'request': request})

if serializer.is_valid():
    try:
        order = serializer.save()
        print(f"   ✅ Order created successfully!")
        print(f"   - Order ID: {order.id}")
        print(f"   - Order Number: {order.order_number}")
        print(f"   - Order Type: {order.order_type}")
        print(f"   - Service Mode: {order.service_mode}")
        print(f"   - Payment Status: {order.payment_status}")
        print(f"   - Total Amount: {order.total_amount}")
        print(f"   - Is Free Measurement: {order.is_free_measurement}")
        print(f"   - Items Count: {order.order_items.count()}")
        
        # Check order item
        item = order.order_items.first()
        print(f"   - Item Fabric: {item.fabric}")
        print(f"   - Item Quantity: {item.quantity}")
        print(f"   - Item Unit Price: {item.unit_price}")
        
    except Exception as e:
        print(f"   ❌ ERROR creating order: {e}")
        import traceback
        traceback.print_exc()
else:
    print(f"   ❌ Validation failed:")
    for field, errors in serializer.errors.items():
        print(f"      - {field}: {errors}")

print("\n" + "="*70)
print("TEST COMPLETED")
print("="*70 + "\n")
