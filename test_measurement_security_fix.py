"""
Test script to verify the security fix for measurement_taken status bypass.

This test verifies that riders cannot set measurement_taken status
without actually adding measurements via the /measurements/ endpoint.

Run with: python manage.py test test_measurement_security_fix
Or: python test_measurement_security_fix.py (if run as standalone)
"""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zthob.settings')
django.setup()

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from apps.orders.models import Order, OrderItem
from apps.tailors.models import TailorProfile, Fabric, FabricCategory
from apps.customers.models import Address, CustomerProfile
from apps.riders.models import RiderProfile

User = get_user_model()


class MeasurementSecurityFixTest(TestCase):
    """Test cases for measurement_taken security fix"""
    
    def setUp(self):
        """Set up test data"""
        # Create customer
        self.customer_user = User.objects.create_user(
            username='test_customer',
            email='customer@test.com',
            password='testpass123',
            role='USER',
            phone_number='+966501234567'
        )
        CustomerProfile.objects.create(user=self.customer_user)
        
        # Create tailor
        self.tailor_user = User.objects.create_user(
            username='test_tailor',
            email='tailor@test.com',
            password='testpass123',
            role='TAILOR',
            phone_number='+966501234568'
        )
        self.tailor_profile = TailorProfile.objects.create(
            user=self.tailor_user,
            shop_name='Test Tailor Shop',
            shop_status=True
        )
        
        # Create rider
        self.rider_user = User.objects.create_user(
            username='test_rider',
            email='rider@test.com',
            password='testpass123',
            role='RIDER',
            phone_number='+966501234569'
        )
        self.rider_profile = RiderProfile.objects.create(
            user=self.rider_user,
            is_approved=True,
            review_status='approved'
        )
        
        # Create fabric category and fabric
        self.category = FabricCategory.objects.create(
            name='Test Category',
            description='Test category'
        )
        self.fabric = Fabric.objects.create(
            tailor=self.tailor_user,
            category=self.category,
            name='Test Fabric',
            price=100.00,
            stock=10,
            is_active=True
        )
        
        # Create delivery address
        self.address = Address.objects.create(
            user=self.customer_user,
            street='123 Test St',
            city='Riyadh',
            state_province='Riyadh Province',
            country='Saudi Arabia',
            postal_code='12345'
        )
        
        # Create fabric_with_stitching order
        self.order = Order.objects.create(
            customer=self.customer_user,
            tailor=self.tailor_user,
            rider=self.rider_user,
            order_type='fabric_with_stitching',
            status='confirmed',
            rider_status='on_way_to_measurement',
            tailor_status='accepted',
            payment_status='paid',
            payment_method='credit_card',
            delivery_address=self.address,
            subtotal=100.00,
            tax_amount=15.00,
            delivery_fee=25.00,
            total_amount=140.00
        )
        
        # Create order item
        OrderItem.objects.create(
            order=self.order,
            fabric=self.fabric,
            quantity=1,
            unit_price=100.00,
            total_price=100.00
        )
        
        # Setup API client
        self.client = APIClient()
        self.client.force_authenticate(user=self.rider_user)
    
    def test_cannot_set_measurement_taken_without_measurements(self):
        """Test that rider cannot set measurement_taken without adding measurements"""
        # Try to update status to measurement_taken without adding measurements
        response = self.client.patch(
            f'/api/riders/orders/{self.order.id}/update-status/',
            {
                'rider_status': 'measurement_taken',
                'notes': 'Trying to bypass measurements'
            },
            format='json'
        )
        
        # Should fail with 400 Bad Request
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertIn('Cannot mark measurements as taken', response.data['message'])
    
    def test_can_set_measurement_taken_after_adding_measurements(self):
        """Test that rider can set measurement_taken after adding measurements via /measurements/ endpoint"""
        # First, add measurements via the proper endpoint
        measurements_data = {
            'chest': '40',
            'waist': '36',
            'shoulder': '18',
            'sleeve_length': '24',
            'length': '42'
        }
        
        response = self.client.post(
            f'/api/riders/orders/{self.order.id}/measurements/',
            {
                'measurements': measurements_data,
                'notes': 'Measurements taken successfully'
            },
            format='json'
        )
        
        # Should succeed
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['rider_status'], 'measurement_taken')
        
        # Verify measurements were stored
        self.order.refresh_from_db()
        self.assertIsNotNone(self.order.rider_measurements)
        self.assertIsNotNone(self.order.measurement_taken_at)
        self.assertEqual(self.order.rider_measurements['chest'], '40')
    
    def test_fabric_only_order_not_affected(self):
        """Test that fabric_only orders are not affected by this validation"""
        # Create a fabric_only order
        fabric_only_order = Order.objects.create(
            customer=self.customer_user,
            tailor=self.tailor_user,
            rider=self.rider_user,
            order_type='fabric_only',
            status='confirmed',
            rider_status='accepted',
            tailor_status='accepted',
            payment_status='paid',
            payment_method='credit_card',
            delivery_address=self.address,
            subtotal=100.00,
            tax_amount=15.00,
            delivery_fee=25.00,
            total_amount=140.00
        )
        
        # Try to update status (fabric_only doesn't have measurement_taken, but test other statuses)
        response = self.client.patch(
            f'/api/riders/orders/{fabric_only_order.id}/update-status/',
            {
                'rider_status': 'on_way_to_pickup',
                'notes': 'On way to pickup'
            },
            format='json'
        )
        
        # Should succeed (fabric_only orders don't need measurements)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
    
    def test_validation_only_applies_to_fabric_with_stitching(self):
        """Test that validation only applies to fabric_with_stitching orders"""
        # Create order without measurements
        self.order.rider_measurements = None
        self.order.measurement_taken_at = None
        self.order.rider_status = 'on_way_to_measurement'
        self.order.save()
        
        # Try to set measurement_taken - should fail
        response = self.client.patch(
            f'/api/riders/orders/{self.order.id}/update-status/',
            {
                'rider_status': 'measurement_taken',
                'notes': 'Trying to bypass'
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
    
    def test_validation_checks_both_measurements_and_timestamp(self):
        """Test that validation checks both rider_measurements and measurement_taken_at"""
        # Case 1: Has measurements but no timestamp
        self.order.rider_measurements = {'chest': '40', 'waist': '36'}
        self.order.measurement_taken_at = None
        self.order.rider_status = 'on_way_to_measurement'
        self.order.save()
        
        response = self.client.patch(
            f'/api/riders/orders/{self.order.id}/update-status/',
            {
                'rider_status': 'measurement_taken',
                'notes': 'Trying to bypass'
            },
            format='json'
        )
        
        # Should fail (missing timestamp)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Case 2: Has timestamp but no measurements
        from django.utils import timezone
        self.order.rider_measurements = None
        self.order.measurement_taken_at = timezone.now()
        self.order.save()
        
        response = self.client.patch(
            f'/api/riders/orders/{self.order.id}/update-status/',
            {
                'rider_status': 'measurement_taken',
                'notes': 'Trying to bypass'
            },
            format='json'
        )
        
        # Should fail (missing measurements)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


if __name__ == '__main__':
    import django
    from django.test.utils import get_runner
    from django.conf import settings
    
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(['test_measurement_security_fix'])
    
    if failures:
        sys.exit(1)
    else:
        print("\n✅ All tests passed! Security fix is working correctly.")
        sys.exit(0)




