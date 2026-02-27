"""
Quick test to verify FSM implementation works correctly
"""
from django.test import TestCase
from apps.orders.models import Order
from apps.users.models import User
from django_fsm import TransitionNotAllowed


class OrderFSMTestCase(TestCase):
    def setUp(self):
        """Create test users"""
        self.customer = User.objects.create_user(
            username='testcustomer',
            email='customer@test.com',
            password='testpass123',
            role='USER'
        )
        self.tailor = User.objects.create_user(
            username='testtailor',
            email='tailor@test.com',
            password='testpass123',
            role='TAILOR'
        )
        self.rider = User.objects.create_user(
            username='testrider',
            email='rider@test.com',
            password='testpass123',
            role='RIDER'
        )
    
    def test_tailor_accept_transition(self):
        """Test tailor can accept order"""
        order = Order.objects.create(
            customer=self.customer,
            tailor=self.tailor,
            order_type='fabric_only',
            subtotal=100,
            tax_amount=10,
            delivery_fee=5
        )
        
        # Initial state
        self.assertEqual(order.tailor_status, 'none')
        self.assertEqual(order.status, 'pending')
        
        # Tailor accepts
        order.tailor_accept_order(user=self.tailor)
        order.save()
        
        # Check transition worked
        self.assertEqual(order.tailor_status, 'accepted')
        # Check auto-sync worked
        self.assertEqual(order.status, 'confirmed')
    
    def test_rider_accept_transition(self):
        """Test rider can accept order"""
        order = Order.objects.create(
            customer=self.customer,
            tailor=self.tailor,
            order_type='fabric_only',
            subtotal=100,
            tax_amount=10,
            delivery_fee=5
        )
        
        # Tailor accepts first
        order.tailor_accept_order()
        order.save()
        
        # Rider accepts
        order.rider_accept_order(user=self.rider)
        order.save()
        
        # Check transition worked
        self.assertEqual(order.rider_status, 'accepted')
        # Check auto-sync worked
        self.assertEqual(order.status, 'in_progress')
    
    def test_fabric_only_complete_flow(self):
        """Test complete fabric_only order flow"""
        order = Order.objects.create(
            customer=self.customer,
            tailor=self.tailor,
            order_type='fabric_only',
            subtotal=100,
            tax_amount=10,
            delivery_fee=5
        )
        
        # 1. Tailor accepts
        order.tailor_accept_order()
        order.save()
        self.assertEqual(order.status, 'confirmed')
        
        # 2. Rider accepts
        order.rider_accept_order()
        order.save()
        self.assertEqual(order.status, 'in_progress')
        
        # 3. Rider goes to pickup
        order.rider_start_pickup()
        order.save()
        self.assertEqual(order.rider_status, 'on_way_to_pickup')
        
        # 4. Rider picks up
        order.rider_mark_picked_up()
        order.save()
        self.assertEqual(order.rider_status, 'picked_up')
        self.assertEqual(order.status, 'ready_for_delivery')
        
        # 5. Rider starts delivery
        order.rider_start_delivery()
        order.save()
        self.assertEqual(order.rider_status, 'on_way_to_delivery')
        
        # 6. Rider delivers
        order.rider_mark_delivered()
        order.save()
        self.assertEqual(order.rider_status, 'delivered')
        self.assertEqual(order.status, 'delivered')
        self.assertIsNotNone(order.actual_delivery_date)
    
    def test_fabric_with_stitching_flow(self):
        """Test fabric_with_stitching order flow"""
        order = Order.objects.create(
            customer=self.customer,
            tailor=self.tailor,
            order_type='fabric_with_stitching',
            subtotal=100,
            tax_amount=10,
            delivery_fee=5
        )
        
        # 1. Tailor accepts
        order.tailor_accept_order()
        order.save()
        self.assertEqual(order.status, 'confirmed')
        
        # 2. Rider accepts
        order.rider_accept_order()
        order.save()
        self.assertEqual(order.status, 'in_progress')
        
        # 3. Rider goes to measurement
        order.rider_start_measurement()
        order.save()
        self.assertEqual(order.rider_status, 'on_way_to_measurement')
        
        # 4. Rider starts measuring
        order.rider_start_measuring()
        order.save()
        self.assertEqual(order.rider_status, 'measuring')
        
        # 5. Measurements complete
        order.rider_complete_measurements()
        order.save()
        self.assertEqual(order.rider_status, 'measurement_taken')
        
        # 6. Tailor starts stitching
        order.tailor_start_stitching()
        order.save()
        self.assertEqual(order.tailor_status, 'stitching_started')
        
        # 7. Tailor finishes stitching
        order.tailor_finish_stitching()
        order.save()
        self.assertEqual(order.tailor_status, 'stitched')
        
        # 8. Rider goes to pickup
        order.rider_start_pickup_after_measurement()
        order.save()
        self.assertEqual(order.rider_status, 'on_way_to_pickup')
        self.assertEqual(order.status, 'ready_for_delivery')
        
        # 9. Rider picks up
        order.rider_mark_picked_up()
        order.save()
        
        # 10. Rider delivers
        order.rider_start_delivery()
        order.save()
        order.rider_mark_delivered()
        order.save()
        self.assertEqual(order.status, 'delivered')
    
    def test_backward_compatibility(self):
        """Test that direct status assignment still works"""
        order = Order.objects.create(
            customer=self.customer,
            tailor=self.tailor,
            order_type='fabric_only',
            subtotal=100,
            tax_amount=10,
            delivery_fee=5
        )
        
        # Old way should still work (protected=False)
        order.tailor_status = 'accepted'
        order.save()
        
        # Auto-sync should still work
        self.assertEqual(order.status, 'confirmed')
