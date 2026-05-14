import os
import django
import sys

# Set up Django environment
sys.path.append('/Users/mac/Documents/GitHub/zthob-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zthob.settings')
django.setup()

from apps.orders.models import Order, OrderItem
from apps.orders.actions import OrderActionManager
from django.contrib.auth import get_user_model
from apps.tailors.models import TailorProfile, Fabric, FabricCategory
from decimal import Decimal

User = get_user_model()

def run_test():
    print("--- Starting Order Action Pattern Test ---")
    
    # 1. Setup Users
    customer, _ = User.objects.get_or_create(username='test_customer', defaults={'role': 'USER', 'phone': '123456789'})
    tailor_user, _ = User.objects.get_or_create(username='test_tailor', defaults={'role': 'TAILOR', 'phone': '987654321'})
    rider_user, _ = User.objects.get_or_create(username='test_rider', defaults={'role': 'RIDER', 'phone': '555555555'})
    
    # Ensure roles are correct in profiles too if necessary
    customer.role = 'USER'
    customer.save()
    tailor_user.role = 'TAILOR'
    tailor_user.save()
    rider_user.role = 'RIDER'
    rider_user.save()

    # 2. Setup Tailor Profile & Fabric
    tailor_profile, _ = TailorProfile.objects.get_or_create(user=tailor_user, defaults={'shop_name': 'Test Shop', 'shop_status': True})
    cat, _ = FabricCategory.objects.get_or_create(name='Test Cat')
    fabric, _ = Fabric.objects.get_or_create(tailor=tailor_profile, name='Test Fabric', defaults={'price': 100, 'category': cat})

    # 3. Create a Pending Order (fabric_with_stitching)
    order = Order.objects.create(
        customer=customer,
        tailor=tailor_user,
        order_type='fabric_with_stitching',
        status='pending',
        service_mode='home_delivery',
        subtotal=100,
        total_amount=115
    )
    OrderItem.objects.create(order=order, fabric=fabric, quantity=1, unit_price=100)

    print(f"Created Order {order.order_number} (Status: {order.status})")

    # 4. Test Available Actions for Tailor
    actions = OrderActionManager.get_available_actions(order, tailor_user)
    print(f"Available actions for Tailor: {[a['key'] for a in actions]}")
    assert 'accept_order' in [a['key'] for a in actions]

    # 5. Tailor Accepts Order
    action = OrderActionManager.get_action('accept_order', order, tailor_user)
    msg = action.execute()
    print(f"Tailor Action: {msg} | New Status: {order.status} | Tailor Status: {order.tailor_status}")
    assert order.status == 'confirmed'
    assert order.tailor_status == 'accepted'

    # 6. Test Rider Actions (Measurements missing)
    actions = OrderActionManager.get_available_actions(order, rider_user)
    print(f"Available actions for Rider: {[a['key'] for a in actions]}")
    assert 'accept_order' in [a['key'] for a in actions]

    # 7. Rider Accepts Order (Case B: No measurements)
    action = OrderActionManager.get_action('accept_order', order, rider_user)
    action.execute()
    print(f"Rider Accepted | Rider Status: {order.rider_status}")
    assert order.rider_status == 'accepted'

    # 8. Rider Starts Measuring
    action = OrderActionManager.get_action('start_measuring', order, rider_user)
    action.execute()
    print(f"Rider Started Measuring | Rider Status: {order.rider_status}")
    assert order.rider_status == 'on_way_to_measurement'

    # 9. Rider Records Measurements
    action = OrderActionManager.get_action('record_measurements', order, rider_user, data={'measurements': {'chest': 40}})
    action.execute()
    print(f"Rider Recorded Measurements | Rider Status: {order.rider_status}")
    assert order.rider_status == 'measurement_taken'
    assert order.all_items_have_measurements is True

    # 10. Tailor Starts Stitching
    actions = OrderActionManager.get_available_actions(order, tailor_user)
    print(f"Available actions for Tailor after measurements: {[a['key'] for a in actions]}")
    assert 'start_stitching' in [a['key'] for a in actions]

    action = OrderActionManager.get_action('start_stitching', order, tailor_user)
    action.execute()
    print(f"Tailor Started Stitching | Tailor Status: {order.tailor_status} | Status: {order.status}")
    assert order.tailor_status == 'stitching_started'
    assert order.status == 'in_progress'

    # 11. Tailor Finishes & Marks Ready
    OrderActionManager.get_action('finish_stitching', order, tailor_user).execute()
    OrderActionManager.get_action('mark_ready', order, tailor_user).execute()
    print(f"Tailor Finished | Tailor Status: {order.tailor_status} | Status: {order.status}")
    assert order.tailor_status == 'stitched'
    assert order.status == 'ready_for_delivery'

    # 12. Rider Delivery
    OrderActionManager.get_action('pickup_order', order, rider_user).execute()
    OrderActionManager.get_action('start_delivery', order, rider_user).execute()
    OrderActionManager.get_action('mark_delivered', order, rider_user).execute()
    print(f"Order Delivered! | Status: {order.status}")
    assert order.status == 'delivered'

    print("\n--- ALL TESTS PASSED SUCCESSFULLY ---")

if __name__ == "__main__":
    run_test()
