"""
Test Suite for Free Measurement Service Feature
SQA Testing - Comprehensive validation
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from apps.customers.models import CustomerProfile, FamilyMember
from apps.tailors.models import TailorProfile
from apps.orders.models import Order, OrderItem
from decimal import Decimal
import json

User = get_user_model()


class MeasurementServiceTestCase(TestCase):
    """Comprehensive tests for measurement service feature"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create customer
        self.customer = User.objects.create_user(
            username='testcustomer',
            email='customer@test.com',
            phone='+966500000001',
            password='testpass123',
            role='USER'
        )
        
        # Create customer profile
        self.customer_profile = CustomerProfile.objects.create(
            user=self.customer,
            first_free_measurement_used=False
        )
        
        # Create family member
        self.family_member = FamilyMember.objects.create(
            user=self.customer,
            name='Wife',
            relationship='spouse',
            gender='female'
        )
        
        # Create tailor
        self.tailor = User.objects.create_user(
            username='testtailor',
            email='tailor@test.com',
            phone='+966500000002',
            password='testpass123',
            role='TAILOR'
        )
        
        # Create tailor profile
        self.tailor_profile = TailorProfile.objects.create(
            user=self.tailor,
            shop_name='Test Tailor Shop',
            shop_status=True
        )
        
        # Get auth tokens
        from rest_framework_simplejwt.tokens import RefreshToken
        
        customer_token = RefreshToken.for_user(self.customer)
        self.customer_token = str(customer_token.access_token)
        
        tailor_token = RefreshToken.for_user(self.tailor)
        self.tailor_token = str(tailor_token.access_token)
    
    def test_01_check_eligibility_true(self):
        """Test eligibility check for new customer"""
        response = self.client.get(
            '/api/orders/measurement-eligibility/',
            HTTP_AUTHORIZATION=f'Bearer {self.customer_token}'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertTrue(data['data']['is_eligible'])
        print("✅ Test 1 PASSED: Eligibility check returns true for new customer")
    
    def test_02_create_walk_in_measurement_single(self):
        """Test creating walk-in measurement order for single person"""
        order_data = {
            'tailor': self.tailor.id,
            'order_type': 'measurement_service',
            'service_mode': 'walk_in',
            'items': [
                {'family_member': None}
            ]
        }
        
        response = self.client.post(
            '/api/orders/create/',
            data=json.dumps(order_data),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.customer_token}'
        )
        
        self.assertEqual(response.status_code, 201, f"Failed: {response.json()}")
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['order_type'], 'measurement_service')
        self.assertEqual(data['data']['service_mode'], 'walk_in')
        self.assertEqual(data['data']['payment_status'], 'paid')
        self.assertEqual(data['data']['total_amount'], '0.00')
        self.assertTrue(data['data']['is_free_measurement'])
        self.assertEqual(len(data['data']['order_items']), 1)
        
        # Check order item
        item = data['data']['order_items'][0]
        self.assertIsNone(item['fabric'])
        self.assertEqual(item['quantity'], 1)
        self.assertEqual(item['unit_price'], '0.00')
        
        print("✅ Test 2 PASSED: Walk-in measurement order created successfully")
        return data['data']['id']
    
    def test_03_create_walk_in_measurement_multi(self):
        """Test creating walk-in measurement order for multiple people"""
        order_data = {
            'tailor': self.tailor.id,
            'order_type': 'measurement_service',
            'service_mode': 'walk_in',
            'items': [
                {'family_member': None},
                {'family_member': self.family_member.id}
            ]
        }
        
        response = self.client.post(
            '/api/orders/create/',
            data=json.dumps(order_data),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.customer_token}'
        )
        
        self.assertEqual(response.status_code, 201, f"Failed: {response.json()}")
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertEqual(len(data['data']['order_items']), 2)
        print("✅ Test 3 PASSED: Multi-person walk-in order created")
    
    def test_04_create_home_delivery_no_tailor(self):
        """Test creating home delivery measurement without tailor"""
        order_data = {
            'order_type': 'measurement_service',
            'service_mode': 'home_delivery',
            'items': [{'family_member': None}],
            'delivery_latitude': 24.7136,
            'delivery_longitude': 46.6753,
            'delivery_formatted_address': 'Riyadh, Saudi Arabia'
        }
        
        response = self.client.post(
            '/api/orders/create/',
            data=json.dumps(order_data),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.customer_token}'
        )
        
        self.assertEqual(response.status_code, 201, f"Failed: {response.json()}")
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertIsNone(data['data']['tailor'])
        print("✅ Test 4 PASSED: Home delivery measurement without tailor created")
    
    def test_05_walk_in_without_tailor_fails(self):
        """Test that walk-in measurement without tailor fails"""
        order_data = {
            'order_type': 'measurement_service',
            'service_mode': 'walk_in',
            'items': [{'family_member': None}]
        }
        
        response = self.client.post(
            '/api/orders/create/',
            data=json.dumps(order_data),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.customer_token}'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('tailor', str(data['errors']).lower())
        print("✅ Test 5 PASSED: Walk-in without tailor correctly fails")
    
    def test_06_second_free_measurement_fails(self):
        """Test that second free measurement is rejected"""
        # Create first order
        self.test_02_create_walk_in_measurement_single()
        
        # Mark as used
        self.customer_profile.first_free_measurement_used = True
        self.customer_profile.save()
        
        # Try to create second order
        order_data = {
            'tailor': self.tailor.id,
            'order_type': 'measurement_service',
            'service_mode': 'walk_in',
            'items': [{'family_member': None}]
        }
        
        response = self.client.post(
            '/api/orders/create/',
            data=json.dumps(order_data),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.customer_token}'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('already used', str(data['errors']).lower())
        print("✅ Test 6 PASSED: Second free measurement correctly rejected")
    
    def test_07_check_eligibility_after_use(self):
        """Test eligibility check after using free measurement"""
        # Mark as used
        self.customer_profile.first_free_measurement_used = True
        self.customer_profile.save()
        
        response = self.client.get(
            '/api/orders/measurement-eligibility/',
            HTTP_AUTHORIZATION=f'Bearer {self.customer_token}'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['data']['is_eligible'])
        print("✅ Test 7 PASSED: Eligibility check returns false after use")


def run_all_tests():
    """Run all tests with detailed output"""
    import sys
    from django.test.runner import DiscoverRunner
    
    print("\n" + "="*70)
    print("🧪 STARTING COMPREHENSIVE MEASUREMENT SERVICE TESTS")
    print("="*70 + "\n")
    
    runner = DiscoverRunner(verbosity=2)
    test_suite = runner.test_loader.loadTestsFromTestCase(MeasurementServiceTestCase)
    result = runner.test_runner.run(test_suite)
    
    print("\n" + "="*70)
    if result.wasSuccessful():
        print("✅ ALL TESTS PASSED!")
    else:
        print(f"❌ {len(result.failures)} TESTS FAILED")
        print(f"❌ {len(result.errors)} TESTS HAD ERRORS")
    print("="*70 + "\n")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    run_all_tests()
