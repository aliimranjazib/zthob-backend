#!/usr/bin/env python
"""
Script to create dummy orders and assign them to a rider
"""
import os
import sys
import django
from datetime import datetime, timedelta

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zthob.settings')
django.setup()

from decimal import Decimal
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.orders.models import Order, OrderItem, OrderStatusHistory
from apps.riders.models import RiderOrderAssignment, RiderProfile, RiderProfileReview
from apps.tailors.models import TailorProfile, Fabric
from apps.customers.models import Address, CustomerProfile
from apps.orders.services import OrderCalculationService

User = get_user_model()

def get_or_create_rider():
    """Get or create the rider user"""
    username = "rider@example.com"
    
    rider, created = User.objects.get_or_create(
        username=username,
        defaults={
            'email': username,
            'role': 'RIDER',
            'is_active': True
        }
    )
    
    if created:
        rider.set_password('password123')
        rider.save()
        print(f"✓ Created rider user: {username}")
    else:
        print(f"✓ Found existing rider user: {username}")
    
    # Ensure rider profile exists
    rider_profile, profile_created = RiderProfile.objects.get_or_create(
        user=rider,
        defaults={
            'full_name': 'Test Rider',
            'phone_number': '+966501234567'
        }
    )
    
    if profile_created:
        print(f"✓ Created rider profile")
    
    # Ensure rider profile review exists and is approved
    review, review_created = RiderProfileReview.objects.get_or_create(
        profile=rider_profile,
        defaults={
            'review_status': 'approved',
            'submitted_at': timezone.now(),
            'reviewed_at': timezone.now()
        }
    )
    
    if review_created:
        print(f"✓ Created rider profile review (approved)")
    else:
        # Update to approved if not already
        if review.review_status != 'approved':
            review.review_status = 'approved'
            review.reviewed_at = timezone.now()
            review.save()
            print(f"✓ Updated rider profile review to approved")
    
    return rider

def get_test_data():
    """Get test customers, tailors, and fabrics"""
    # Get a customer
    customer = User.objects.filter(role='USER').first()
    if not customer:
        print("⚠ No customer found. Creating one...")
        customer = User.objects.create_user(
            username='test_customer',
            email='customer@test.com',
            password='password123',
            role='USER'
        )
        CustomerProfile.objects.create(user=customer)
    
    # Get a tailor
    tailor_user = User.objects.filter(role='TAILOR').first()
    if not tailor_user:
        print("⚠ No tailor found. Creating one...")
        tailor_user = User.objects.create_user(
            username='test_tailor',
            email='tailor@test.com',
            password='password123',
            role='TAILOR'
        )
        TailorProfile.objects.create(
            user=tailor_user,
            shop_name='Test Tailor Shop',
            shop_status=True
        )
    
    tailor_profile = TailorProfile.objects.get(user=tailor_user)
    
    # Get or create fabrics
    fabrics = []
    for i in range(3):
        fabric, created = Fabric.objects.get_or_create(
            name=f'Test Fabric {i+1}',
            tailor=tailor_profile,
            defaults={
                'price': Decimal('50.00') + (i * Decimal('10.00')),
                'stock': 100,
                'is_active': True,
                'sku': f'FAB-TEST-{i+1}'
            }
        )
        fabrics.append(fabric)
    
    # Get or create delivery address
    address, created = Address.objects.get_or_create(
        user=customer,
        defaults={
            'street': '123 Test Street',
            'city': 'Riyadh',
            'country': 'Saudi Arabia',
            'zip_code': '12345',
            'address_tag': 'home'
        }
    )
    
    return customer, tailor_user, fabrics, address

def create_order(order_type, customer, tailor, fabrics, address, rider, order_num):
    """Create a single order"""
    
    # Select fabric and quantity
    fabric = fabrics[order_num % len(fabrics)]
    quantity = (order_num % 3) + 1  # 1, 2, or 3
    
    # Calculate totals
    items_data = [{'fabric': fabric, 'quantity': quantity}]
    distance_km = 8.5 + (order_num * 2)  # Vary distance: 8.5, 10.5, 12.5, 14.5, 16.5
    
    totals = OrderCalculationService.calculate_all_totals(
        items_data=items_data,
        distance_km=distance_km,
        delivery_address=address,
        tailor=tailor
    )
    
    # Create order
    order = Order.objects.create(
        customer=customer,
        tailor=tailor,
        rider=rider,  # Assign rider immediately
        order_type=order_type,
        order_number=f'ORD-TEST-{order_num:03d}',
        status='confirmed' if order_type == 'fabric_only' else 'measuring',
        payment_status='paid',  # Must be paid for rider assignment
        payment_method='cod',
        delivery_address=address,
        estimated_delivery_date=timezone.now().date() + timedelta(days=7),
        special_instructions=f'Test order {order_num} - {order_type}',
        subtotal=totals['subtotal'],
        tax_amount=totals['tax_amount'],
        delivery_fee=totals['delivery_fee'],
        total_amount=totals['total_amount']
    )
    
    # Create order item
    OrderItem.objects.create(
        order=order,
        fabric=fabric,
        quantity=quantity,
        unit_price=fabric.price,
        total_price=fabric.price * quantity,
        measurements={'chest': '40', 'waist': '32'} if order_type == 'fabric_with_stitching' else {},
        custom_instructions=f'Custom instructions for order {order_num}'
    )
    
    # Create order status history
    OrderStatusHistory.objects.create(
        order=order,
        status=order.status,
        previous_status=None,
        changed_by=tailor,
        notes=f'Order created and assigned to rider'
    )
    
    # Create rider assignment
    RiderOrderAssignment.objects.create(
        order=order,
        rider=rider,
        status='accepted',
        accepted_at=timezone.now()
    )
    
    # Update fabric stock
    fabric.stock -= quantity
    fabric.save()
    
    return order

def main():
    """Main function"""
    print("=" * 60)
    print("CREATING RIDER ORDERS")
    print("=" * 60)
    
    # Get or create rider
    rider = get_or_create_rider()
    
    # Get test data
    customer, tailor, fabrics, address = get_test_data()
    
    print(f"\n✓ Customer: {customer.username}")
    print(f"✓ Tailor: {tailor.username}")
    print(f"✓ Rider: {rider.username}")
    print(f"✓ Fabrics available: {len(fabrics)}")
    
    # Create 5 orders
    orders = []
    order_types = ['fabric_only', 'fabric_with_stitching', 'fabric_only', 'fabric_with_stitching', 'fabric_only']
    
    print("\n" + "=" * 60)
    print("CREATING ORDERS")
    print("=" * 60)
    
    for i, order_type in enumerate(order_types, 1):
        try:
            order = create_order(order_type, customer, tailor, fabrics, address, rider, i)
            orders.append(order)
            
            print(f"\n✓ Order {i} Created:")
            print(f"  - Order Number: {order.order_number}")
            print(f"  - Type: {order.order_type}")
            print(f"  - Status: {order.status}")
            print(f"  - Payment Status: {order.payment_status}")
            print(f"  - Rider: {order.rider.username}")
            print(f"  - Subtotal: {order.subtotal} SAR")
            print(f"  - Tax: {order.tax_amount} SAR")
            print(f"  - Delivery Fee: {order.delivery_fee} SAR")
            print(f"  - Total: {order.total_amount} SAR")
            print(f"  - Items: {order.order_items.count()}")
            
        except Exception as e:
            print(f"\n✗ Failed to create order {i}: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"✓ Total orders created: {len(orders)}")
    print(f"✓ Fabric Only orders: {sum(1 for o in orders if o.order_type == 'fabric_only')}")
    print(f"✓ Fabric With Stitching orders: {sum(1 for o in orders if o.order_type == 'fabric_with_stitching')}")
    print(f"✓ All orders assigned to rider: {rider.username}")
    print(f"✓ All orders have payment_status='paid'")
    
    print("\n" + "=" * 60)
    print("ORDER DETAILS")
    print("=" * 60)
    for order in orders:
        print(f"\n{order.order_number}:")
        print(f"  Type: {order.order_type}")
        print(f"  Status: {order.status}")
        print(f"  Total: {order.total_amount} SAR")
        print(f"  Rider: {order.rider.username if order.rider else 'None'}")
    
    print("\n✓ All orders created successfully!")
    print("=" * 60)

if __name__ == '__main__':
    main()

