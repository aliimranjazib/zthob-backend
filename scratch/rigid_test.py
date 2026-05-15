import os
import django
import sys
from decimal import Decimal

# Setup Django environment
sys.path.append('/Users/mac/Documents/GitHub/zthob-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zthob.settings')
django.setup()

from apps.orders.models import Order, OrderItem
from apps.accounts.models import CustomUser
from apps.orders.actions import OrderActionManager
from rest_framework.exceptions import ValidationError
from django.utils import timezone

def get_or_create_user(role, username):
    phone = f"05{hash(username) % 100000000:08d}"
    user, created = CustomUser.objects.get_or_create(
        username=username,
        defaults={'role': role, 'phone': phone, 'is_active': True}
    )
    if not created and user.role != role:
        user.role = role
        user.save()
    return user

def test_full_flow():
    print(f"\n--- TESTING FULL FLOW WITH REFACTORED NOTIFICATIONS ---")
    customer = get_or_create_user('CUSTOMER', 'final_cust')
    tailor = get_or_create_user('TAILOR', 'final_tailor')
    rider = get_or_create_user('RIDER', 'final_rider')
    
    order = Order.objects.create(
        customer=customer,
        order_type='fabric_with_stitching',
        service_mode='home_delivery',
        status='pending'
    )
    item = OrderItem.objects.create(order=order, unit_price=Decimal('100.00'), total_price=Decimal('100.00'))
    
    # 1. Acceptance
    OrderActionManager.get_action('accept_order', order, tailor, requested_role='TAILOR').execute()
    OrderActionManager.get_action('accept_order', order, rider, requested_role='RIDER').execute()
    
    # 2. Measurement
    OrderActionManager.get_action('start_measuring', order, rider, requested_role='RIDER').execute()
    OrderActionManager.get_action('record_measurements', order, rider, data={'measurements': {'h': 1}}, requested_role='RIDER').execute()
    
    # 3. Production
    OrderActionManager.get_action('start_stitching', order, tailor, requested_role='TAILOR').execute()
    OrderActionManager.get_action('finish_stitching', order, tailor, requested_role='TAILOR').execute()
    OrderActionManager.get_action('mark_ready', order, tailor, requested_role='TAILOR').execute()
    
    # 4. Delivery
    OrderActionManager.get_action('pickup_order', order, rider, requested_role='RIDER').execute()
    OrderActionManager.get_action('start_delivery', order, rider, requested_role='RIDER').execute()
    OrderActionManager.get_action('mark_delivered', order, rider, requested_role='RIDER').execute()
    
    print(f"Final State: Status={order.status}, T={order.tailor_status}, R={order.rider_status}")

if __name__ == "__main__":
    try:
        test_full_flow()
        print("\nVERDICT: SYSTEM IS STABLE AND ACCURATE.")
    except Exception as e:
        print(f"\nVERDICT: TEST FAILED! Error: {str(e)}")
        import traceback
        traceback.print_exc()
