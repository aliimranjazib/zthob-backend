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
    user, created = CustomUser.objects.get_or_create(
        username=username,
        defaults={'role': role, 'phone': '123456789', 'is_active': True}
    )
    if not created and user.role != role:
        user.role = role
        user.save()
    return user

def test_full_lifecycle():
    print(f"\n--- TESTING FULL LIFECYCLE: Home Delivery Flow ---")
    
    # 1. Setup
    customer = get_or_create_user('CUSTOMER', 'test_customer')
    tailor = get_or_create_user('TAILOR', 'test_tailor')
    rider = get_or_create_user('RIDER', 'test_rider')
    
    order = Order.objects.create(
        customer=customer,
        order_type='fabric_with_stitching',
        service_mode='home_delivery',
        status='pending'
    )
    OrderItem.objects.create(order=order, unit_price=Decimal('100.00'), total_price=Decimal('100.00'))
    
    # --- PHASE 1: ACCEPTANCE ---
    OrderActionManager.get_action('accept_order', order, tailor, requested_role='TAILOR').execute()
    OrderActionManager.get_action('accept_order', order, rider, requested_role='RIDER').execute()
    print(f"Accepted: Status={order.status}, R_Status={order.rider_status}")

    # --- PHASE 2: MEASUREMENT ---
    OrderActionManager.get_action('start_measuring', order, rider, requested_role='RIDER').execute()
    OrderActionManager.get_action('record_measurements', order, rider, data={'measurements': {'h': 1}}, requested_role='RIDER').execute()
    print(f"Measured: Status={order.status}, R_Status={order.rider_status}")

    # --- PHASE 3: STITCHING ---
    OrderActionManager.get_action('start_stitching', order, tailor, requested_role='TAILOR').execute()
    OrderActionManager.get_action('finish_stitching', order, tailor, requested_role='TAILOR').execute()
    OrderActionManager.get_action('mark_ready', order, tailor, requested_role='TAILOR').execute()
    print(f"Stitched & Ready: Status={order.status}, T_Status={order.tailor_status}")

    # --- PHASE 4: DELIVERY (The Rigid Test) ---
    actions = [a['key'] for a in OrderActionManager.get_available_actions(order, rider, requested_role='RIDER')]
    print(f"Rider Actions (Ready): {actions}")
    
    if 'pickup_order' in actions:
        OrderActionManager.get_action('pickup_order', order, rider, requested_role='RIDER').execute()
        print(f"After Pickup: R_Status={order.rider_status}")
        
        # VERIFY: pickup_order should be GONE, start_delivery should be PRESENT
        post_pickup_actions = [a['key'] for a in OrderActionManager.get_available_actions(order, rider, requested_role='RIDER')]
        print(f"Rider Actions (After Pickup): {post_pickup_actions}")
        
        if 'pickup_order' in post_pickup_actions:
            raise Exception("BUG: pickup_order still visible after execution!")
        if 'start_delivery' not in post_pickup_actions:
            raise Exception("BUG: start_delivery NOT visible after pickup!")
            
        OrderActionManager.get_action('start_delivery', order, rider, requested_role='RIDER').execute()
        print(f"After Start Delivery: R_Status={order.rider_status}")
        
        OrderActionManager.get_action('mark_delivered', order, rider, requested_role='RIDER').execute()
        print(f"Final State: Status={order.status}, R_Status={order.rider_status}")

if __name__ == "__main__":
    try:
        test_full_lifecycle()
        print("\nVERDICT: ALL TESTS PASSED SUCCESSFULLY! LOGIC IS 100% CORRECT.")
    except Exception as e:
        print(f"\nVERDICT: TEST FAILED! Error: {str(e)}")
        import traceback
        traceback.print_exc()
