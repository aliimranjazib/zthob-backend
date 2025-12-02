"""
Test cases for Rider Analytics API
"""
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status
from apps.orders.models import Order
from apps.riders.models import RiderProfile, RiderProfileReview
from apps.riders.services import RiderAnalyticsService
from apps.tailors.models import TailorProfile
from apps.customers.models import Address

User = get_user_model()


class RiderAnalyticsServiceTestCase(TestCase):
    """Test cases for RiderAnalyticsService"""
    
    def setUp(self):
        """Set up test data"""
        # Create users
        self.rider_user = User.objects.create_user(
            username='test_rider',
            email='rider@test.com',
            password='testpass123',
            role='RIDER'
        )
        
        self.customer_user = User.objects.create_user(
            username='test_customer',
            email='customer@test.com',
            password='testpass123',
            role='USER'
        )
        
        self.tailor_user = User.objects.create_user(
            username='test_tailor',
            email='tailor@test.com',
            password='testpass123',
            role='TAILOR'
        )
        
        # Create rider profile
        self.rider_profile = RiderProfile.objects.create(
            user=self.rider_user,
            full_name='Test Rider',
            phone_number='+966501234567'
        )
        
        # Create rider profile review (approved)
        RiderProfileReview.objects.create(
            profile=self.rider_profile,
            review_status='approved',
            submitted_at=timezone.now(),
            reviewed_at=timezone.now()
        )
        
        # Create tailor profile
        self.tailor_profile = TailorProfile.objects.create(
            user=self.tailor_user,
            shop_name='Test Tailor Shop',
            shop_status=True
        )
        
        # Create delivery address
        self.address = Address.objects.create(
            user=self.customer_user,
            street='123 Test St',
            city='Test City',
            postal_code='12345'
        )
    
    def test_get_rider_orders(self):
        """Test getting orders for a rider"""
        # Create orders assigned to rider
        order1 = Order.objects.create(
            customer=self.customer_user,
            tailor=self.tailor_user,
            rider=self.rider_user,
            status='delivered',
            subtotal=Decimal('100.00'),
            tax_amount=Decimal('15.00'),
            delivery_fee=Decimal('25.00'),
            total_amount=Decimal('140.00')
        )
        
        order2 = Order.objects.create(
            customer=self.customer_user,
            tailor=self.tailor_user,
            rider=self.rider_user,
            status='pending',
            subtotal=Decimal('200.00'),
            tax_amount=Decimal('30.00'),
            delivery_fee=Decimal('25.00'),
            total_amount=Decimal('255.00')
        )
        
        # Create order not assigned to this rider
        Order.objects.create(
            customer=self.customer_user,
            tailor=self.tailor_user,
            rider=None,
            status='delivered',
            total_amount=Decimal('100.00')
        )
        
        orders = RiderAnalyticsService.get_rider_orders(self.rider_user)
        self.assertEqual(orders.count(), 2)
        
        # Test with status filter
        delivered_orders = RiderAnalyticsService.get_rider_orders(
            self.rider_user,
            status_filter='delivered'
        )
        self.assertEqual(delivered_orders.count(), 1)
        self.assertEqual(delivered_orders.first().id, order1.id)
    
    def test_get_completed_deliveries_count(self):
        """Test completed deliveries count"""
        # Create delivered orders
        for i in range(5):
            Order.objects.create(
                customer=self.customer_user,
                tailor=self.tailor_user,
                rider=self.rider_user,
                status='delivered',
                delivery_fee=Decimal('25.00'),
                total_amount=Decimal('100.00')
            )
        
        # Create pending orders (should not be counted)
        for i in range(3):
            Order.objects.create(
                customer=self.customer_user,
                tailor=self.tailor_user,
                rider=self.rider_user,
                status='pending',
                delivery_fee=Decimal('25.00'),
                total_amount=Decimal('100.00')
            )
        
        count = RiderAnalyticsService.get_completed_deliveries_count(self.rider_user)
        self.assertEqual(count, 5)
    
    def test_get_total_orders_count(self):
        """Test total orders count (excluding cancelled)"""
        # Create various orders
        for i in range(5):
            Order.objects.create(
                customer=self.customer_user,
                tailor=self.tailor_user,
                rider=self.rider_user,
                status='delivered',
                total_amount=Decimal('100.00')
            )
        
        for i in range(3):
            Order.objects.create(
                customer=self.customer_user,
                tailor=self.tailor_user,
                rider=self.rider_user,
                status='pending',
                total_amount=Decimal('100.00')
            )
        
        # Cancelled orders should not be counted
        for i in range(2):
            Order.objects.create(
                customer=self.customer_user,
                tailor=self.tailor_user,
                rider=self.rider_user,
                status='cancelled',
                total_amount=Decimal('100.00')
            )
        
        count = RiderAnalyticsService.get_total_orders_count(self.rider_user)
        self.assertEqual(count, 8)  # 5 delivered + 3 pending
    
    def test_calculate_completion_percentage(self):
        """Test completion percentage calculation"""
        # Create 10 delivered orders
        for i in range(10):
            Order.objects.create(
                customer=self.customer_user,
                tailor=self.tailor_user,
                rider=self.rider_user,
                status='delivered',
                total_amount=Decimal('100.00')
            )
        
        # Create 5 pending orders
        for i in range(5):
            Order.objects.create(
                customer=self.customer_user,
                tailor=self.tailor_user,
                rider=self.rider_user,
                status='pending',
                total_amount=Decimal('100.00')
            )
        
        stats = RiderAnalyticsService.calculate_completion_percentage(self.rider_user)
        self.assertEqual(stats['completed_deliveries'], 10)
        self.assertEqual(stats['total_orders'], 15)
        self.assertAlmostEqual(stats['completion_percentage'], 66.67, places=1)
        self.assertIn('%', stats['formatted_percentage'])
    
    def test_calculate_completion_percentage_zero_orders(self):
        """Test completion percentage with no orders"""
        stats = RiderAnalyticsService.calculate_completion_percentage(self.rider_user)
        self.assertEqual(stats['completed_deliveries'], 0)
        self.assertEqual(stats['total_orders'], 0)
        self.assertEqual(stats['completion_percentage'], 0.0)
    
    def test_calculate_total_delivery_fees(self):
        """Test total delivery fees calculation"""
        # Create delivered orders with delivery fees
        order1 = Order.objects.create(
            customer=self.customer_user,
            tailor=self.tailor_user,
            rider=self.rider_user,
            status='delivered',
            delivery_fee=Decimal('25.00'),
            total_amount=Decimal('100.00')
        )
        
        order2 = Order.objects.create(
            customer=self.customer_user,
            tailor=self.tailor_user,
            rider=self.rider_user,
            status='delivered',
            delivery_fee=Decimal('30.00'),
            total_amount=Decimal('150.00')
        )
        
        # Create pending order (should not be counted)
        Order.objects.create(
            customer=self.customer_user,
            tailor=self.tailor_user,
            rider=self.rider_user,
            status='pending',
            delivery_fee=Decimal('25.00'),
            total_amount=Decimal('100.00')
        )
        
        total_fees = RiderAnalyticsService.calculate_total_delivery_fees(self.rider_user)
        self.assertEqual(total_fees, Decimal('55.00'))
    
    def test_calculate_daily_deliveries(self):
        """Test daily deliveries calculation"""
        today = timezone.now().date()
        
        # Create orders for different dates
        order1 = Order.objects.create(
            customer=self.customer_user,
            tailor=self.tailor_user,
            rider=self.rider_user,
            status='delivered',
            delivery_fee=Decimal('25.00'),
            total_amount=Decimal('100.00'),
            actual_delivery_date=today - timedelta(days=1)
        )
        
        order2 = Order.objects.create(
            customer=self.customer_user,
            tailor=self.tailor_user,
            rider=self.rider_user,
            status='delivered',
            delivery_fee=Decimal('30.00'),
            total_amount=Decimal('150.00'),
            actual_delivery_date=today - timedelta(days=1)
        )
        
        order3 = Order.objects.create(
            customer=self.customer_user,
            tailor=self.tailor_user,
            rider=self.rider_user,
            status='delivered',
            delivery_fee=Decimal('25.00'),
            total_amount=Decimal('100.00'),
            actual_delivery_date=today
        )
        
        daily_deliveries = RiderAnalyticsService.calculate_daily_deliveries(
            self.rider_user,
            days=7
        )
        
        # Should have 7 days of data
        self.assertEqual(len(daily_deliveries), 7)
        
        # Find yesterday's data
        yesterday_data = next(
            (day for day in daily_deliveries if day['date'] == (today - timedelta(days=1)).isoformat()),
            None
        )
        self.assertIsNotNone(yesterday_data)
        self.assertEqual(yesterday_data['deliveries_count'], 2)
        self.assertEqual(Decimal(yesterday_data['delivery_fees']), Decimal('55.00'))
        
        # Find today's data
        today_data = next(
            (day for day in daily_deliveries if day['date'] == today.isoformat()),
            None
        )
        self.assertIsNotNone(today_data)
        self.assertEqual(today_data['deliveries_count'], 1)
        self.assertEqual(Decimal(today_data['delivery_fees']), Decimal('25.00'))
    
    def test_get_weekly_delivery_trends(self):
        """Test weekly delivery trends"""
        now = timezone.now()
        
        # Create orders for different weeks
        for i in range(3):
            Order.objects.create(
                customer=self.customer_user,
                tailor=self.tailor_user,
                rider=self.rider_user,
                status='delivered',
                delivery_fee=Decimal('25.00'),
                total_amount=Decimal('100.00'),
                created_at=now - timedelta(weeks=1, days=i)
            )
        
        for i in range(2):
            Order.objects.create(
                customer=self.customer_user,
                tailor=self.tailor_user,
                rider=self.rider_user,
                status='pending',
                delivery_fee=Decimal('25.00'),
                total_amount=Decimal('100.00'),
                created_at=now - timedelta(weeks=2, days=i)
            )
        
        trends = RiderAnalyticsService.get_weekly_delivery_trends(
            self.rider_user,
            weeks=4
        )
        
        self.assertGreater(len(trends), 0)
        # Check that we have data for recent weeks
        self.assertTrue(any('orders_assigned' in week for week in trends))
        self.assertTrue(any('deliveries_completed' in week for week in trends))
        self.assertTrue(any('delivery_fees' in week for week in trends))
    
    def test_get_comprehensive_analytics(self):
        """Test comprehensive analytics method"""
        # Create some test orders
        for i in range(5):
            Order.objects.create(
                customer=self.customer_user,
                tailor=self.tailor_user,
                rider=self.rider_user,
                status='delivered',
                delivery_fee=Decimal('25.00'),
                total_amount=Decimal('100.00'),
                actual_delivery_date=timezone.now().date() - timedelta(days=i)
            )
        
        for i in range(3):
            Order.objects.create(
                customer=self.customer_user,
                tailor=self.tailor_user,
                rider=self.rider_user,
                status='pending',
                delivery_fee=Decimal('25.00'),
                total_amount=Decimal('100.00')
            )
        
        analytics = RiderAnalyticsService.get_comprehensive_analytics(
            self.rider_user,
            days=30,
            weeks=12
        )
        
        # Check all required fields are present
        self.assertIn('total_delivery_fees', analytics)
        self.assertIn('formatted_total_delivery_fees', analytics)
        self.assertIn('completed_deliveries_count', analytics)
        self.assertIn('total_orders_count', analytics)
        self.assertIn('completion_percentage', analytics)
        self.assertIn('formatted_completion_percentage', analytics)
        self.assertIn('daily_deliveries', analytics)
        self.assertIn('weekly_trends', analytics)
        self.assertIn('analytics_period', analytics)
        
        # Check values
        self.assertEqual(analytics['completed_deliveries_count'], 5)
        self.assertEqual(analytics['total_orders_count'], 8)
        self.assertGreater(float(analytics['total_delivery_fees']), 0)
        self.assertEqual(len(analytics['daily_deliveries']), 30)
        self.assertEqual(len(analytics['weekly_trends']), 12)


class RiderAnalyticsAPITestCase(TestCase):
    """Test cases for Rider Analytics API endpoint"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        # Create rider user
        self.rider_user = User.objects.create_user(
            username='test_rider',
            email='rider@test.com',
            password='testpass123',
            role='RIDER'
        )
        
        # Create rider profile
        self.rider_profile = RiderProfile.objects.create(
            user=self.rider_user,
            full_name='Test Rider',
            phone_number='+966501234567'
        )
        
        # Create rider profile review (approved)
        RiderProfileReview.objects.create(
            profile=self.rider_profile,
            review_status='approved',
            submitted_at=timezone.now(),
            reviewed_at=timezone.now()
        )
        
        # Create customer user
        self.customer_user = User.objects.create_user(
            username='test_customer',
            email='customer@test.com',
            password='testpass123',
            role='USER'
        )
        
        # Create tailor user
        self.tailor_user = User.objects.create_user(
            username='test_tailor',
            email='tailor@test.com',
            password='testpass123',
            role='TAILOR'
        )
        
        # Create tailor profile
        self.tailor_profile = TailorProfile.objects.create(
            user=self.tailor_user,
            shop_name='Test Tailor Shop'
        )
        
        # Create some test orders
        for i in range(3):
            Order.objects.create(
                customer=self.customer_user,
                tailor=self.tailor_user,
                rider=self.rider_user,
                status='delivered',
                delivery_fee=Decimal('25.00'),
                total_amount=Decimal('100.00'),
                actual_delivery_date=timezone.now().date() - timedelta(days=i)
            )
    
    def test_analytics_endpoint_requires_authentication(self):
        """Test that analytics endpoint requires authentication"""
        response = self.client.get('/api/riders/analytics/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_analytics_endpoint_requires_rider_role(self):
        """Test that analytics endpoint requires rider role"""
        self.client.force_authenticate(user=self.customer_user)
        response = self.client.get('/api/riders/analytics/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(response.data['success'])
        self.assertIn('Only riders', response.data['message'])
    
    def test_analytics_endpoint_success(self):
        """Test successful analytics endpoint call"""
        self.client.force_authenticate(user=self.rider_user)
        response = self.client.get('/api/riders/analytics/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('data', response.data)
        
        analytics_data = response.data['data']
        self.assertIn('total_delivery_fees', analytics_data)
        self.assertIn('formatted_total_delivery_fees', analytics_data)
        self.assertIn('completed_deliveries_count', analytics_data)
        self.assertIn('total_orders_count', analytics_data)
        self.assertIn('completion_percentage', analytics_data)
        self.assertIn('formatted_completion_percentage', analytics_data)
        self.assertIn('daily_deliveries', analytics_data)
        self.assertIn('weekly_trends', analytics_data)
        self.assertIn('analytics_period', analytics_data)
    
    def test_analytics_endpoint_with_custom_parameters(self):
        """Test analytics endpoint with custom days and weeks parameters"""
        self.client.force_authenticate(user=self.rider_user)
        response = self.client.get('/api/riders/analytics/?days=60&weeks=24')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        analytics_data = response.data['data']
        self.assertEqual(len(analytics_data['daily_deliveries']), 60)
        self.assertEqual(len(analytics_data['weekly_trends']), 24)
        self.assertEqual(analytics_data['analytics_period']['daily_deliveries_days'], 60)
        self.assertEqual(analytics_data['analytics_period']['weekly_trends_weeks'], 24)
    
    def test_analytics_endpoint_invalid_parameters(self):
        """Test analytics endpoint with invalid parameters"""
        self.client.force_authenticate(user=self.rider_user)
        
        # Test invalid days parameter (too high)
        response = self.client.get('/api/riders/analytics/?days=500')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertIn('Days parameter must be between', response.data['message'])
        
        # Test invalid days parameter (too low)
        response = self.client.get('/api/riders/analytics/?days=0')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Test invalid weeks parameter (too high)
        response = self.client.get('/api/riders/analytics/?weeks=100')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertIn('Weeks parameter must be between', response.data['message'])
        
        # Test invalid weeks parameter (too low)
        response = self.client.get('/api/riders/analytics/?weeks=0')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Test non-integer parameters
        response = self.client.get('/api/riders/analytics/?days=abc')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertIn('Invalid query parameters', response.data['message'])
        
        # Test non-integer weeks
        response = self.client.get('/api/riders/analytics/?weeks=xyz')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_analytics_endpoint_data_structure(self):
        """Test that analytics endpoint returns correct data structure"""
        self.client.force_authenticate(user=self.rider_user)
        response = self.client.get('/api/riders/analytics/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        analytics_data = response.data['data']
        
        # Check daily_deliveries structure
        self.assertIsInstance(analytics_data['daily_deliveries'], list)
        if len(analytics_data['daily_deliveries']) > 0:
            day_data = analytics_data['daily_deliveries'][0]
            self.assertIn('date', day_data)
            self.assertIn('deliveries_count', day_data)
            self.assertIn('delivery_fees', day_data)
            self.assertIn('formatted_delivery_fees', day_data)
        
        # Check weekly_trends structure
        self.assertIsInstance(analytics_data['weekly_trends'], list)
        if len(analytics_data['weekly_trends']) > 0:
            week_data = analytics_data['weekly_trends'][0]
            self.assertIn('week_start', week_data)
            self.assertIn('week_end', week_data)
            self.assertIn('week_label', week_data)
            self.assertIn('orders_assigned', week_data)
            self.assertIn('deliveries_completed', week_data)
            self.assertIn('delivery_fees', week_data)
            self.assertIn('formatted_delivery_fees', week_data)
        
        # Check analytics_period structure
        period = analytics_data['analytics_period']
        self.assertIn('daily_deliveries_days', period)
        self.assertIn('weekly_trends_weeks', period)
        self.assertIn('generated_at', period)
    
    def test_analytics_endpoint_with_no_orders(self):
        """Test analytics endpoint when rider has no orders"""
        # Create a new rider with no orders
        new_rider = User.objects.create_user(
            username='new_rider',
            email='newrider@test.com',
            password='testpass123',
            role='RIDER'
        )
        
        rider_profile = RiderProfile.objects.create(
            user=new_rider,
            full_name='New Rider',
            phone_number='+966509876543'
        )
        
        RiderProfileReview.objects.create(
            profile=rider_profile,
            review_status='approved',
            submitted_at=timezone.now(),
            reviewed_at=timezone.now()
        )
        
        self.client.force_authenticate(user=new_rider)
        response = self.client.get('/api/riders/analytics/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        analytics_data = response.data['data']
        self.assertEqual(analytics_data['completed_deliveries_count'], 0)
        self.assertEqual(analytics_data['total_orders_count'], 0)
        self.assertEqual(float(analytics_data['total_delivery_fees']), 0.0)
        self.assertEqual(analytics_data['completion_percentage'], 0.0)
        self.assertEqual(len(analytics_data['daily_deliveries']), 30)  # Should still have 30 days
        self.assertEqual(len(analytics_data['weekly_trends']), 12)  # Should still have 12 weeks

