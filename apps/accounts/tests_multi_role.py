from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from apps.accounts.models import CustomUser
from apps.core.models import PhoneVerification
from apps.customers.models import CustomerProfile
from apps.tailors.models import TailorProfile
from apps.riders.models import RiderProfile
from apps.core.services import PhoneVerificationService

class MultiRoleAuthenticationTestCase(TestCase):
    """Test cases for multi-role identity management"""
    
    def setUp(self):
        self.client = APIClient()
        self.phone_login_url = reverse('accounts:phone-login')
        self.phone_verify_url = reverse('accounts:phone-verify')
        self.test_phone = '0500000000' # One of the TEST_PHONES in PhoneVerificationService
        self.test_otp = PhoneVerificationService.TEST_OTP
        
    def test_unified_identity_lifecycle(self):
        """
        Test that a single phone number can register as USER, 
        then TAILOR, then RIDER, and keep the same identity.
        """
        # 1. Register as a Customer (USER)
        self.client.post(self.phone_login_url, {'phone': self.test_phone})
        response = self.client.post(self.phone_verify_url, {
            'phone': self.test_phone,
            'otp_code': self.test_otp,
            'name': 'Test User',
            'role': 'USER'
        })
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = CustomUser.objects.get(phone=self.test_phone)
        self.assertTrue(user.is_customer)
        self.assertFalse(user.is_tailor)
        self.assertFalse(user.is_rider)
        
        # 2. Register same phone as a Tailor
        self.client.post(self.phone_login_url, {'phone': self.test_phone})
        response = self.client.post(self.phone_verify_url, {
            'phone': self.test_phone,
            'otp_code': self.test_otp,
            'role': 'TAILOR'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK) # Existing user login
        user.refresh_from_db()
        self.assertTrue(user.is_customer, "Should still be a customer")
        self.assertTrue(user.is_tailor, "Should now ALSO be a tailor")
        self.assertFalse(user.is_rider)
        
        # 3. Register same phone as a Rider
        self.client.post(self.phone_login_url, {'phone': self.test_phone})
        response = self.client.post(self.phone_verify_url, {
            'phone': self.test_phone,
            'otp_code': self.test_otp,
            'role': 'RIDER'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.is_customer)
        self.assertTrue(user.is_tailor)
        self.assertTrue(user.is_rider, "Should now ALSO be a rider")
        
        # Verify all profiles are linked to the same user
        self.assertEqual(CustomerProfile.objects.filter(user=user).count(), 1)
        self.assertEqual(TailorProfile.objects.filter(user=user).count(), 1)
        self.assertEqual(RiderProfile.objects.filter(user=user).count(), 1)

    def test_api_response_contains_all_roles(self):
        """Test that the API response correctly reports all active roles"""
        # Register as Customer
        self.client.post(self.phone_login_url, {'phone': self.test_phone})
        self.client.post(self.phone_verify_url, {
            'phone': self.test_phone,
            'otp_code': self.test_otp,
            'role': 'USER'
        })
        
        # Then "Login/Register" as Tailor
        self.client.post(self.phone_login_url, {'phone': self.test_phone})
        response = self.client.post(self.phone_verify_url, {
            'phone': self.test_phone,
            'otp_code': self.test_otp,
            'role': 'TAILOR'
        })
        
        user_data = response.data['data']['user']
        self.assertIn('USER', user_data['all_roles'])
        self.assertIn('TAILOR', user_data['all_roles'])
        self.assertTrue(user_data['is_customer'])
        self.assertTrue(user_data['is_tailor'])
        self.assertFalse(user_data['is_rider'])
