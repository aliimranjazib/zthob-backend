"""
Test cases for Order Status Info and Lightweight Response Features

Tests cover:
1. status_info field in list APIs (OrderListSerializer, RiderOrderListSerializer)
2. status_info field in detail APIs (OrderSerializer)
3. Lightweight response serializer (OrderStatusUpdateResponseSerializer)
4. Next available actions based on role and order state
5. Status transitions validation
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal
from rest_framework.test import APIClient
from rest_framework import status
from apps.orders.models import Order, OrderItem, OrderStatusHistory
from apps.orders.services import OrderStatusTransitionService
from apps.orders.serializers import (
    OrderListSerializer,
    OrderSerializer,
    OrderStatusUpdateResponseSerializer
)
from apps.tailors.models import TailorProfile, Fabric, FabricCategory
from apps.customers.models import Address
from apps.riders.models import RiderProfile
from apps.riders.serializers import RiderOrderListSerializer

User = get_user_model()


class OrderStatusInfoTest(TestCase):
    """Test status_info field in order serializers"""
    
    def setUp(self):
        """Set up test data"""
        # Create customer
        self.customer = User.objects.create_user(
            username='test_customer',
            email='customer@test.com',
            password='testpass123',
            role='USER'
        )
        
        # Create tailor
        self.tailor = User.objects.create_user(
            username='test_tailor',
            email='tailor@test.com',
            password='testpass123',
            role='TAILOR'
        )
        self.tailor_profile, _ = TailorProfile.objects.get_or_create(
            user=self.tailor,
            defaults={
                'shop_name': 'Test Tailor Shop',
                'shop_status': True
            }
        )
        
        # Create rider
        self.rider = User.objects.create_user(
            username='test_rider',
            email='rider@test.com',
            password='testpass123',
            role='RIDER'
        )
        self.rider_profile, _ = RiderProfile.objects.get_or_create(
            user=self.rider,
            defaults={
                'full_name': 'Test Rider',
                'phone_number': '+966501234567'
            }
        )
        # Create review with approved status
        from apps.riders.models import RiderProfileReview
        RiderProfileReview.objects.get_or_create(
            profile=self.rider_profile,
            defaults={'review_status': 'approved'}
        )
        
        # Create fabric
        self.fabric_category = FabricCategory.objects.create(
            name='Fabric',
            slug='fabric'
        )
        self.fabric = Fabric.objects.create(
            tailor=self.tailor_profile,
            name='Test Fabric',
            price=Decimal('100.00'),
            stock=10,
            is_active=True,
            category=self.fabric_category
        )
        
        # Create address
        self.address = Address.objects.create(
            user=self.customer,
            street='123 Test St',
            city='Riyadh',
            country='Saudi Arabia'
        )
        
        # Create order
        self.order = Order.objects.create(
            customer=self.customer,
            tailor=self.tailor,
            order_type='fabric_only',
            payment_method='cod',
            delivery_address=self.address,
            status='pending',
            payment_status='pending',
            subtotal=Decimal('100.00'),
            tax_amount=Decimal('15.00'),
            delivery_fee=Decimal('25.00'),
            total_amount=Decimal('140.00')
        )
        
        OrderItem.objects.create(
            order=self.order,
            fabric=self.fabric,
            quantity=1,
            unit_price=Decimal('100.00')
        )
        
        # Create mock request
        self.mock_request = type('obj', (object,), {'user': self.tailor})()
    
    def test_order_list_serializer_includes_status_info(self):
        """Test that OrderListSerializer includes status_info field"""
        serializer = OrderListSerializer(
            self.order,
            context={'request': self.mock_request}
        )
        data = serializer.data
        
        self.assertIn('status_info', data)
        self.assertIsNotNone(data['status_info'])
    
    def test_status_info_structure(self):
        """Test that status_info has correct structure"""
        serializer = OrderListSerializer(
            self.order,
            context={'request': self.mock_request}
        )
        status_info = serializer.data['status_info']
        
        # Check required fields
        self.assertIn('current_status', status_info)
        self.assertIn('current_rider_status', status_info)
        self.assertIn('current_tailor_status', status_info)
        self.assertIn('next_available_actions', status_info)
        self.assertIn('can_cancel', status_info)
        self.assertIn('status_progress', status_info)
        
        # Check types
        self.assertIsInstance(status_info['next_available_actions'], list)
        self.assertIsInstance(status_info['can_cancel'], bool)
        self.assertIsInstance(status_info['status_progress'], dict)
    
    def test_status_info_for_pending_order_tailor(self):
        """Test status_info for pending order viewed by tailor"""
        serializer = OrderListSerializer(
            self.order,
            context={'request': self.mock_request}
        )
        status_info = serializer.data['status_info']
        
        self.assertEqual(status_info['current_status'], 'pending')
        self.assertEqual(status_info['current_tailor_status'], 'none')
        
        # Tailor should see 'confirmed' action
        actions = status_info['next_available_actions']
        action_values = [a['value'] for a in actions]
        self.assertIn('confirmed', action_values)
    
    def test_status_info_for_confirmed_order_tailor(self):
        """Test status_info for confirmed order viewed by tailor"""
        self.order.status = 'confirmed'
        self.order.tailor_status = 'accepted'
        self.order.save()
        
        serializer = OrderListSerializer(
            self.order,
            context={'request': self.mock_request}
        )
        status_info = serializer.data['status_info']
        
        self.assertEqual(status_info['current_status'], 'confirmed')
        
        # Tailor should see 'in_progress' action
        actions = status_info['next_available_actions']
        action_values = [a['value'] for a in actions]
        self.assertIn('in_progress', action_values)
    
    def test_status_info_for_rider(self):
        """Test status_info for order viewed by rider"""
        self.order.status = 'confirmed'
        self.order.rider = self.rider
        self.order.save()
        
        mock_request = type('obj', (object,), {'user': self.rider})()
        serializer = RiderOrderListSerializer(
            self.order,
            context={'request': mock_request}
        )
        status_info = serializer.data['status_info']
        
        self.assertIsNotNone(status_info)
        self.assertEqual(status_info['current_status'], 'confirmed')
    
    def test_next_available_actions_structure(self):
        """Test that next_available_actions have correct structure"""
        serializer = OrderListSerializer(
            self.order,
            context={'request': self.mock_request}
        )
        actions = serializer.data['status_info']['next_available_actions']
        
        if actions:  # If there are actions
            action = actions[0]
            self.assertIn('type', action)
            self.assertIn('value', action)
            self.assertIn('label', action)
            self.assertIn('description', action)
            self.assertIn('role', action)
            self.assertIn('requires_confirmation', action)
            # Icon should NOT be present
            self.assertNotIn('icon', action)
    
    def test_status_progress_structure(self):
        """Test that status_progress has correct structure"""
        serializer = OrderListSerializer(
            self.order,
            context={'request': self.mock_request}
        )
        progress = serializer.data['status_info']['status_progress']
        
        self.assertIn('current_step', progress)
        self.assertIn('total_steps', progress)
        self.assertIn('percentage', progress)
        
        self.assertIsInstance(progress['current_step'], int)
        self.assertIsInstance(progress['total_steps'], int)
        self.assertIsInstance(progress['percentage'], int)
        self.assertGreaterEqual(progress['percentage'], 0)
        self.assertLessEqual(progress['percentage'], 100)
    
    def test_status_info_without_request_context(self):
        """Test that status_info returns None when no request context"""
        serializer = OrderListSerializer(self.order)
        status_info = serializer.data.get('status_info')
        
        self.assertIsNone(status_info)


class OrderStatusUpdateResponseSerializerTest(TestCase):
    """Test lightweight OrderStatusUpdateResponseSerializer"""
    
    def setUp(self):
        """Set up test data"""
        self.customer = User.objects.create_user(
            username='test_customer',
            email='customer@test.com',
            password='testpass123',
            role='USER'
        )
        
        self.tailor = User.objects.create_user(
            username='test_tailor',
            email='tailor@test.com',
            password='testpass123',
            role='TAILOR'
        )
        self.tailor_profile, _ = TailorProfile.objects.get_or_create(
            user=self.tailor,
            defaults={
                'shop_name': 'Test Tailor Shop',
                'shop_status': True
            }
        )
        
        self.fabric_category = FabricCategory.objects.create(
            name='Fabric',
            slug='fabric'
        )
        self.fabric = Fabric.objects.create(
            tailor=self.tailor_profile,
            name='Test Fabric',
            price=Decimal('100.00'),
            stock=10,
            is_active=True,
            category=self.fabric_category
        )
        
        self.address = Address.objects.create(
            user=self.customer,
            street='123 Test St',
            city='Riyadh',
            country='Saudi Arabia'
        )
        
        self.order = Order.objects.create(
            customer=self.customer,
            tailor=self.tailor,
            order_type='fabric_only',
            payment_method='cod',
            delivery_address=self.address,
            status='pending',
            payment_status='pending',
            subtotal=Decimal('100.00'),
            tax_amount=Decimal('15.00'),
            delivery_fee=Decimal('25.00'),
            total_amount=Decimal('140.00')
        )
        
        self.mock_request = type('obj', (object,), {'user': self.tailor})()
    
    def test_lightweight_serializer_fields(self):
        """Test that OrderStatusUpdateResponseSerializer only returns essential fields"""
        serializer = OrderStatusUpdateResponseSerializer(
            self.order,
            context={'request': self.mock_request}
        )
        data = serializer.data
        
        # Should include these fields
        self.assertIn('id', data)
        self.assertIn('order_number', data)
        self.assertIn('status', data)
        self.assertIn('rider_status', data)
        self.assertIn('tailor_status', data)
        self.assertIn('status_info', data)
        self.assertIn('updated_at', data)
        
        # Should NOT include these fields
        self.assertNotIn('customer_name', data)
        self.assertNotIn('tailor_name', data)
        self.assertNotIn('items', data)
        self.assertNotIn('subtotal', data)
        self.assertNotIn('tax_amount', data)
        self.assertNotIn('delivery_fee', data)
        self.assertNotIn('total_amount', data)
        self.assertNotIn('payment_status', data)
    
    def test_lightweight_serializer_includes_status_info(self):
        """Test that lightweight serializer includes status_info"""
        serializer = OrderStatusUpdateResponseSerializer(
            self.order,
            context={'request': self.mock_request}
        )
        data = serializer.data
        
        self.assertIn('status_info', data)
        self.assertIsNotNone(data['status_info'])


class OrderStatusTransitionServiceTest(TestCase):
    """Test OrderStatusTransitionService for rider acceptance"""
    
    def setUp(self):
        """Set up test data"""
        self.customer = User.objects.create_user(
            username='test_customer',
            email='customer@test.com',
            password='testpass123',
            role='USER'
        )
        
        self.tailor = User.objects.create_user(
            username='test_tailor',
            email='tailor@test.com',
            password='testpass123',
            role='TAILOR'
        )
        self.tailor_profile, _ = TailorProfile.objects.get_or_create(
            user=self.tailor,
            defaults={
                'shop_name': 'Test Tailor Shop',
                'shop_status': True
            }
        )
        
        self.rider = User.objects.create_user(
            username='test_rider',
            email='rider@test.com',
            password='testpass123',
            role='RIDER'
        )
        
        self.fabric_category = FabricCategory.objects.create(
            name='Fabric',
            slug='fabric'
        )
        self.fabric = Fabric.objects.create(
            tailor=self.tailor_profile,
            name='Test Fabric',
            price=Decimal('100.00'),
            stock=10,
            is_active=True,
            category=self.fabric_category
        )
        
        self.address = Address.objects.create(
            user=self.customer,
            street='123 Test St',
            city='Riyadh',
            country='Saudi Arabia'
        )
    
    def test_rider_can_accept_confirmed_order(self):
        """Test that rider can accept order when status is confirmed"""
        order = Order.objects.create(
            customer=self.customer,
            tailor=self.tailor,
            order_type='fabric_only',
            status='confirmed',
            rider_status='none',
            payment_status='paid'
        )
        
        transitions = OrderStatusTransitionService.get_allowed_transitions(
            order, 'RIDER'
        )
        
        self.assertIn('accepted', transitions['rider_status'])
    
    def test_rider_can_accept_ready_for_delivery_order(self):
        """Test that rider can accept order when status is ready_for_delivery"""
        order = Order.objects.create(
            customer=self.customer,
            tailor=self.tailor,
            order_type='fabric_only',
            status='ready_for_delivery',
            rider_status='none',
            payment_status='paid'
        )
        
        transitions = OrderStatusTransitionService.get_allowed_transitions(
            order, 'RIDER'
        )
        
        self.assertIn('accepted', transitions['rider_status'])
    
    def test_rider_can_accept_in_progress_order(self):
        """Test that rider can accept order when status is in_progress"""
        order = Order.objects.create(
            customer=self.customer,
            tailor=self.tailor,
            order_type='fabric_only',
            status='in_progress',
            rider_status='none',
            payment_status='paid'
        )
        
        transitions = OrderStatusTransitionService.get_allowed_transitions(
            order, 'RIDER'
        )
        
        self.assertIn('accepted', transitions['rider_status'])
    
    def test_rider_cannot_skip_accepted_to_pickup(self):
        """Test that rider cannot skip from none to on_way_to_pickup"""
        order = Order.objects.create(
            customer=self.customer,
            tailor=self.tailor,
            order_type='fabric_only',
            status='ready_for_delivery',
            rider_status='none',
            payment_status='paid'
        )
        
        transitions = OrderStatusTransitionService.get_allowed_transitions(
            order, 'RIDER'
        )
        
        # Should only allow 'accepted', not 'on_way_to_pickup'
        self.assertIn('accepted', transitions['rider_status'])
        self.assertNotIn('on_way_to_pickup', transitions['rider_status'])


class OrderStatusUpdateAPITest(TestCase):
    """Test status update API endpoints return lightweight responses"""
    
    def setUp(self):
        """Set up test data"""
        self.customer = User.objects.create_user(
            username='test_customer',
            email='customer@test.com',
            password='testpass123',
            role='USER'
        )
        
        self.tailor = User.objects.create_user(
            username='test_tailor',
            email='tailor@test.com',
            password='testpass123',
            role='TAILOR'
        )
        self.tailor_profile, _ = TailorProfile.objects.get_or_create(
            user=self.tailor,
            defaults={
                'shop_name': 'Test Tailor Shop',
                'shop_status': True
            }
        )
        
        self.fabric_category = FabricCategory.objects.create(
            name='Fabric',
            slug='fabric'
        )
        self.fabric = Fabric.objects.create(
            tailor=self.tailor_profile,
            name='Test Fabric',
            price=Decimal('100.00'),
            stock=10,
            is_active=True,
            category=self.fabric_category
        )
        
        self.address = Address.objects.create(
            user=self.customer,
            street='123 Test St',
            city='Riyadh',
            country='Saudi Arabia'
        )
        
        self.order = Order.objects.create(
            customer=self.customer,
            tailor=self.tailor,
            order_type='fabric_only',
            payment_method='cod',
            delivery_address=self.address,
            status='pending',
            payment_status='pending',
            subtotal=Decimal('100.00'),
            tax_amount=Decimal('15.00'),
            delivery_fee=Decimal('25.00'),
            total_amount=Decimal('140.00')
        )
        
        self.client = APIClient()
        self.client.force_authenticate(user=self.tailor)
    
    def test_status_update_returns_lightweight_response(self):
        """Test that status update endpoint returns lightweight response"""
        url = f'/api/orders/{self.order.id}/status/'
        data = {
            'status': 'confirmed',
            'tailor_status': 'accepted'
        }
        
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get('success'))
        
        order_data = response.data['data']
        
        # Should include essential fields
        self.assertIn('id', order_data)
        self.assertIn('order_number', order_data)
        self.assertIn('status', order_data)
        self.assertIn('rider_status', order_data)
        self.assertIn('tailor_status', order_data)
        self.assertIn('status_info', order_data)
        self.assertIn('updated_at', order_data)
        
        # Should NOT include heavy fields
        self.assertNotIn('items', order_data)
        self.assertNotIn('customer_name', order_data)
        self.assertNotIn('subtotal', order_data)
        self.assertNotIn('total_amount', order_data)
    
    def test_status_update_response_includes_status_info(self):
        """Test that status update response includes status_info"""
        url = f'/api/orders/{self.order.id}/status/'
        data = {
            'status': 'confirmed',
            'tailor_status': 'accepted'
        }
        
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order_data = response.data['data']
        
        self.assertIn('status_info', order_data)
        status_info = order_data['status_info']
        self.assertIn('next_available_actions', status_info)
        self.assertIn('status_progress', status_info)

