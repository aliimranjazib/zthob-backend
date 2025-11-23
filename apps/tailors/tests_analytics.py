"""
Test cases for Tailor Analytics API
"""
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status
from apps.orders.models import Order, OrderItem
from apps.tailors.models import TailorProfile, Fabric, FabricCategory, FabricType
from apps.tailors.services import TailorAnalyticsService
from apps.customers.models import Address

User = get_user_model()


class TailorAnalyticsServiceTestCase(TestCase):
    """Test cases for TailorAnalyticsService"""
    
    def setUp(self):
        """Set up test data"""
        # Create users
        self.tailor_user = User.objects.create_user(
            username='test_tailor',
            email='tailor@test.com',
            password='testpass123',
            role='TAILOR'
        )
        
        self.customer_user = User.objects.create_user(
            username='test_customer',
            email='customer@test.com',
            password='testpass123',
            role='USER'
        )
        
        # Create tailor profile
        self.tailor_profile = TailorProfile.objects.create(
            user=self.tailor_user,
            shop_name='Test Tailor Shop',
            shop_status=True
        )
        
        # Create fabric category and type
        self.category = FabricCategory.objects.create(
            name='Test Category',
            slug='test-category',
            is_active=True
        )
        
        self.fabric_type = FabricType.objects.create(
            name='Cotton',
            slug='cotton'
        )
        
        # Create fabric
        self.fabric = Fabric.objects.create(
            tailor=self.tailor_profile,
            category=self.category,
            fabric_type=self.fabric_type,
            name='Test Fabric',
            price=Decimal('100.00'),
            stock=10,
            is_active=True
        )
        
        # Create delivery address
        self.address = Address.objects.create(
            user=self.customer_user,
            street='123 Test St',
            city='Test City',
            postal_code='12345'
        )
    
    def test_calculate_total_revenue(self):
        """Test total revenue calculation"""
        # Create delivered orders
        order1 = Order.objects.create(
            customer=self.customer_user,
            tailor=self.tailor_user,
            status='delivered',
            subtotal=Decimal('100.00'),
            tax_amount=Decimal('15.00'),
            delivery_fee=Decimal('20.00'),
            total_amount=Decimal('135.00'),
            payment_status='paid'
        )
        
        order2 = Order.objects.create(
            customer=self.customer_user,
            tailor=self.tailor_user,
            status='delivered',
            subtotal=Decimal('200.00'),
            tax_amount=Decimal('30.00'),
            delivery_fee=Decimal('20.00'),
            total_amount=Decimal('250.00'),
            payment_status='paid'
        )
        
        # Create pending order (should not be counted)
        Order.objects.create(
            customer=self.customer_user,
            tailor=self.tailor_user,
            status='pending',
            total_amount=Decimal('100.00'),
            payment_status='pending'
        )
        
        revenue = TailorAnalyticsService.calculate_total_revenue(self.tailor_user)
        self.assertEqual(revenue, Decimal('385.00'))
    
    def test_get_completed_orders_count(self):
        """Test completed orders count"""
        # Create delivered orders
        for i in range(5):
            Order.objects.create(
                customer=self.customer_user,
                tailor=self.tailor_user,
                status='delivered',
                total_amount=Decimal('100.00'),
                payment_status='paid'
            )
        
        # Create pending orders (should not be counted)
        for i in range(3):
            Order.objects.create(
                customer=self.customer_user,
                tailor=self.tailor_user,
                status='pending',
                total_amount=Decimal('100.00'),
                payment_status='pending'
            )
        
        count = TailorAnalyticsService.get_completed_orders_count(self.tailor_user)
        self.assertEqual(count, 5)
    
    def test_get_total_orders_count(self):
        """Test total orders count (excluding cancelled)"""
        # Create various orders
        for i in range(5):
            Order.objects.create(
                customer=self.customer_user,
                tailor=self.tailor_user,
                status='delivered',
                total_amount=Decimal('100.00')
            )
        
        for i in range(3):
            Order.objects.create(
                customer=self.customer_user,
                tailor=self.tailor_user,
                status='pending',
                total_amount=Decimal('100.00')
            )
        
        # Cancelled orders should not be counted
        for i in range(2):
            Order.objects.create(
                customer=self.customer_user,
                tailor=self.tailor_user,
                status='cancelled',
                total_amount=Decimal('100.00')
            )
        
        count = TailorAnalyticsService.get_total_orders_count(self.tailor_user)
        self.assertEqual(count, 8)  # 5 delivered + 3 pending
    
    def test_calculate_completion_percentage(self):
        """Test completion percentage calculation"""
        # Create 10 delivered orders
        for i in range(10):
            Order.objects.create(
                customer=self.customer_user,
                tailor=self.tailor_user,
                status='delivered',
                total_amount=Decimal('100.00')
            )
        
        # Create 5 pending orders
        for i in range(5):
            Order.objects.create(
                customer=self.customer_user,
                tailor=self.tailor_user,
                status='pending',
                total_amount=Decimal('100.00')
            )
        
        stats = TailorAnalyticsService.calculate_completion_percentage(self.tailor_user)
        self.assertEqual(stats['completed_orders'], 10)
        self.assertEqual(stats['total_orders'], 15)
        self.assertAlmostEqual(stats['completion_percentage'], 66.67, places=1)
    
    def test_calculate_completion_percentage_zero_orders(self):
        """Test completion percentage with no orders"""
        stats = TailorAnalyticsService.calculate_completion_percentage(self.tailor_user)
        self.assertEqual(stats['completed_orders'], 0)
        self.assertEqual(stats['total_orders'], 0)
        self.assertEqual(stats['completion_percentage'], 0.0)
    
    def test_calculate_daily_earnings(self):
        """Test daily earnings calculation"""
        today = timezone.now().date()
        
        # Create orders for different dates
        order1 = Order.objects.create(
            customer=self.customer_user,
            tailor=self.tailor_user,
            status='delivered',
            total_amount=Decimal('100.00'),
            actual_delivery_date=today - timedelta(days=1),
            payment_status='paid'
        )
        
        order2 = Order.objects.create(
            customer=self.customer_user,
            tailor=self.tailor_user,
            status='delivered',
            total_amount=Decimal('200.00'),
            actual_delivery_date=today - timedelta(days=1),
            payment_status='paid'
        )
        
        order3 = Order.objects.create(
            customer=self.customer_user,
            tailor=self.tailor_user,
            status='delivered',
            total_amount=Decimal('150.00'),
            actual_delivery_date=today,
            payment_status='paid'
        )
        
        daily_earnings = TailorAnalyticsService.calculate_daily_earnings(
            self.tailor_user, 
            days=7
        )
        
        # Find yesterday's earnings
        yesterday_data = next(
            (day for day in daily_earnings if day['date'] == (today - timedelta(days=1)).isoformat()),
            None
        )
        self.assertIsNotNone(yesterday_data)
        self.assertEqual(Decimal(yesterday_data['earnings']), Decimal('300.00'))
        
        # Find today's earnings
        today_data = next(
            (day for day in daily_earnings if day['date'] == today.isoformat()),
            None
        )
        self.assertIsNotNone(today_data)
        self.assertEqual(Decimal(today_data['earnings']), Decimal('150.00'))
    
    def test_get_weekly_order_trends(self):
        """Test weekly order trends"""
        now = timezone.now()
        
        # Create orders for different weeks
        for i in range(3):
            Order.objects.create(
                customer=self.customer_user,
                tailor=self.tailor_user,
                status='delivered',
                total_amount=Decimal('100.00'),
                created_at=now - timedelta(weeks=1, days=i),
                payment_status='paid'
            )
        
        for i in range(2):
            Order.objects.create(
                customer=self.customer_user,
                tailor=self.tailor_user,
                status='pending',
                total_amount=Decimal('100.00'),
                created_at=now - timedelta(weeks=2, days=i),
                payment_status='pending'
            )
        
        trends = TailorAnalyticsService.get_weekly_order_trends(
            self.tailor_user,
            weeks=4
        )
        
        self.assertGreater(len(trends), 0)
        # Check that we have data for recent weeks
        self.assertTrue(any('orders_created' in week for week in trends))


class TailorAnalyticsAPITestCase(TestCase):
    """Test cases for Tailor Analytics API endpoint"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        # Create tailor user
        self.tailor_user = User.objects.create_user(
            username='test_tailor',
            email='tailor@test.com',
            password='testpass123',
            role='TAILOR'
        )
        
        # Create customer user
        self.customer_user = User.objects.create_user(
            username='test_customer',
            email='customer@test.com',
            password='testpass123',
            role='USER'
        )
        
        # Create tailor profile
        self.tailor_profile = TailorProfile.objects.create(
            user=self.tailor_user,
            shop_name='Test Tailor Shop'
        )
    
    def test_analytics_endpoint_requires_authentication(self):
        """Test that analytics endpoint requires authentication"""
        response = self.client.get('/api/tailors/analytics/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_analytics_endpoint_requires_tailor_role(self):
        """Test that analytics endpoint requires tailor role"""
        self.client.force_authenticate(user=self.customer_user)
        response = self.client.get('/api/tailors/analytics/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_analytics_endpoint_success(self):
        """Test successful analytics endpoint call"""
        self.client.force_authenticate(user=self.tailor_user)
        response = self.client.get('/api/tailors/analytics/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('data', response.data)
        
        analytics_data = response.data['data']
        self.assertIn('total_revenue', analytics_data)
        self.assertIn('completed_orders_count', analytics_data)
        self.assertIn('total_orders_count', analytics_data)
        self.assertIn('completion_percentage', analytics_data)
        self.assertIn('daily_earnings', analytics_data)
        self.assertIn('weekly_trends', analytics_data)
    
    def test_analytics_endpoint_with_custom_parameters(self):
        """Test analytics endpoint with custom days and weeks parameters"""
        self.client.force_authenticate(user=self.tailor_user)
        response = self.client.get('/api/tailors/analytics/?days=60&weeks=24')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        analytics_data = response.data['data']
        self.assertEqual(len(analytics_data['daily_earnings']), 60)
    
    def test_analytics_endpoint_invalid_parameters(self):
        """Test analytics endpoint with invalid parameters"""
        self.client.force_authenticate(user=self.tailor_user)
        
        # Test invalid days parameter
        response = self.client.get('/api/tailors/analytics/?days=500')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Test invalid weeks parameter
        response = self.client.get('/api/tailors/analytics/?weeks=100')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Test non-integer parameters
        response = self.client.get('/api/tailors/analytics/?days=abc')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

