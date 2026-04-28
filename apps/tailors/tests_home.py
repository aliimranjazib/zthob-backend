from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from apps.orders.models import Order
from apps.tailors.models import TailorProfile
from decimal import Decimal

User = get_user_model()

class TailorHomeAPITest(APITestCase):
    def setUp(self):
        # Create a Tailor
        self.tailor_user = User.objects.create_user(
            username='tailor_test', 
            password='password123',
            role='TAILOR'
        )
        # Profile is created automatically by signal
        self.tailor_profile = self.tailor_user.tailor_profile
        self.tailor_profile.shop_name = 'Test Shop'
        self.tailor_profile.shop_status = True
        self.tailor_profile.save()
        
        # Create a Customer
        self.customer_user = User.objects.create_user(
            username='customer_test',
            password='password123',
            role='USER'
        )
        
        self.client.force_authenticate(user=self.tailor_user)
        self.url = reverse('tailor-home')

    def test_get_home_data(self):
        # 1. Create some orders
        # New order
        Order.objects.create(
            customer=self.customer_user,
            tailor=self.tailor_user,
            status='pending',
            subtotal=Decimal('100.00'),
            total_amount=Decimal('100.00')
        )
        
        # Express order + Stitching Started
        Order.objects.create(
            customer=self.customer_user,
            tailor=self.tailor_user,
            status='in_progress',
            tailor_status='stitching_started',
            is_express=True,
            subtotal=Decimal('150.00'),
            total_amount=Decimal('150.00')
        )
        
        # Stitched order
        Order.objects.create(
            customer=self.customer_user,
            tailor=self.tailor_user,
            status='in_progress',
            tailor_status='stitched',
            subtotal=Decimal('120.00'),
            total_amount=Decimal('120.00')
        )

        # Completed order today
        Order.objects.create(
            customer=self.customer_user,
            tailor=self.tailor_user,
            status='delivered',
            subtotal=Decimal('200.00'),
            total_amount=Decimal('200.00')
        )
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data['data']
        
        # Verify counters
        self.assertEqual(data['counters']['new_orders'], 1)
        self.assertEqual(data['counters']['in_progress'], 2)
        self.assertEqual(data['counters']['express_orders'], 1)
        self.assertEqual(float(data['counters']['revenue_today']), 200.0)
        
        # Verify pipeline breakdown
        self.assertEqual(data['pipeline']['new'], 1)
        self.assertEqual(data['pipeline']['stitching'], 1)
        self.assertEqual(data['pipeline']['stitched'], 1)
        
        # Verify lists
        self.assertEqual(len(data['express_orders']), 1)
        self.assertEqual(data['express_orders'][0]['order_number'].startswith('ORD-'), True)
        
        # Verify shop status
        self.assertEqual(data['shop_status']['is_open'], True)

    def test_order_list_filtering(self):
        # Create orders with different statuses
        Order.objects.create(
            customer=self.customer_user,
            tailor=self.tailor_user,
            status='pending',
            subtotal=Decimal('100.00'),
            total_amount=Decimal('100.00')
        )
        Order.objects.create(
            customer=self.customer_user,
            tailor=self.tailor_user,
            status='in_progress',
            tailor_status='stitching_started',
            subtotal=Decimal('100.00'),
            total_amount=Decimal('100.00')
        )
        
        list_url = reverse('orders:tailor-orders')
        
        # Test pending filter
        response = self.client.get(f"{list_url}?status=pending")
        self.assertEqual(len(response.data['data']), 1)
        self.assertEqual(response.data['data'][0]['status'], 'pending')
        
        # Test tailor_status filter
        response = self.client.get(f"{list_url}?tailor_status=stitching_started")
        self.assertEqual(len(response.data['data']), 1)
        self.assertEqual(response.data['data'][0]['status'], 'in_progress')

    def test_unauthorized_access(self):
        self.client.force_authenticate(user=self.customer_user)
        response = self.client.get(self.url)
        # Should be forbidden for non-tailors
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
