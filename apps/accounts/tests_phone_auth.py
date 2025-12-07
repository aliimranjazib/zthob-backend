"""
Test cases for phone-based authentication
"""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from apps.accounts.models import CustomUser
from apps.core.models import PhoneVerification
from django.utils import timezone
from datetime import timedelta


class PhoneAuthenticationTestCase(TestCase):
    """Test cases for phone-based authentication endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        self.phone_login_url = reverse('phone-login')
        self.phone_verify_url = reverse('phone-verify')
        self.phone_resend_url = reverse('phone-resend-otp')
        self.test_phone = '0501234567'
        self.test_phone_formatted = '+966501234567'
    
    def test_phone_login_send_otp_success(self):
        """Test successful OTP sending"""
        response = self.client.post(self.phone_login_url, {
            'phone': self.test_phone
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('OTP sent', response.data['message'])
        self.assertIn('data', response.data)
        self.assertEqual(response.data['data']['phone'], self.test_phone)
        self.assertIn('sms_sent', response.data['data'])
        self.assertIn('expires_in', response.data['data'])
        
        # Verify PhoneVerification record was created
        user = CustomUser.objects.filter(phone=self.test_phone).first()
        self.assertIsNotNone(user)
        verification = PhoneVerification.objects.filter(user=user).latest('created_at')
        self.assertIsNotNone(verification)
        self.assertFalse(verification.is_verified)
    
    def test_phone_login_invalid_phone_format(self):
        """Test OTP sending with invalid phone format"""
        response = self.client.post(self.phone_login_url, {
            'phone': '12345'  # Invalid format
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertIn('errors', response.data)
    
    def test_phone_login_accepts_different_formats(self):
        """Test that different phone formats are accepted"""
        formats = [
            '0501234567',      # Standard Saudi format
            '501234567',       # Without leading 0
            '+966501234567',   # E.164 format
            '966501234567',    # With country code
        ]
        
        for phone_format in formats:
            with self.subTest(phone=phone_format):
                response = self.client.post(self.phone_login_url, {
                    'phone': phone_format
                })
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertTrue(response.data['success'])
    
    def test_phone_verify_new_user_registration(self):
        """Test OTP verification for new user (auto-registration)"""
        # First, send OTP
        self.client.post(self.phone_login_url, {
            'phone': self.test_phone
        })
        
        # Get the OTP from the verification record
        user = CustomUser.objects.filter(phone=self.test_phone).first()
        verification = PhoneVerification.objects.filter(user=user).latest('created_at')
        otp_code = verification.otp_code
        
        # Verify OTP with name and role
        response = self.client.post(self.phone_verify_url, {
            'phone': self.test_phone,
            'otp_code': otp_code,
            'name': 'Ahmed Ali',
            'role': 'USER'
        })
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertIn('tokens', response.data['data'])
        self.assertIn('access_token', response.data['data']['tokens'])
        self.assertIn('refresh_token', response.data['data']['tokens'])
        self.assertIn('user', response.data['data'])
        self.assertTrue(response.data['data']['is_new_user'])
        
        # Verify user was created with correct data
        user.refresh_from_db()
        self.assertEqual(user.first_name, 'Ahmed')
        self.assertEqual(user.last_name, 'Ali')
        self.assertEqual(user.role, 'USER')
        self.assertTrue(user.phone_verified)
    
    def test_phone_verify_existing_user_login(self):
        """Test OTP verification for existing user (login)"""
        # Create existing user
        existing_user = CustomUser.objects.create_user(
            username='existing_user',
            phone=self.test_phone,
            first_name='Existing',
            last_name='User',
            email='existing@example.com'
        )
        
        # Send OTP
        self.client.post(self.phone_login_url, {
            'phone': self.test_phone
        })
        
        # Get the OTP
        verification = PhoneVerification.objects.filter(user=existing_user).latest('created_at')
        otp_code = verification.otp_code
        
        # Verify OTP
        response = self.client.post(self.phone_verify_url, {
            'phone': self.test_phone,
            'otp_code': otp_code
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('tokens', response.data['data'])
        self.assertFalse(response.data['data']['is_new_user'])
        
        # Verify user data is preserved
        existing_user.refresh_from_db()
        self.assertEqual(existing_user.first_name, 'Existing')
        self.assertTrue(existing_user.phone_verified)
    
    def test_phone_verify_invalid_otp(self):
        """Test OTP verification with invalid OTP"""
        # Send OTP first
        self.client.post(self.phone_login_url, {
            'phone': self.test_phone
        })
        
        # Try to verify with wrong OTP
        response = self.client.post(self.phone_verify_url, {
            'phone': self.test_phone,
            'otp_code': '999999'  # Wrong OTP
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertIn('Invalid', response.data['message'])
    
    def test_phone_verify_expired_otp(self):
        """Test OTP verification with expired OTP"""
        # Send OTP
        self.client.post(self.phone_login_url, {
            'phone': self.test_phone
        })
        
        # Get verification and manually expire it
        user = CustomUser.objects.filter(phone=self.test_phone).first()
        verification = PhoneVerification.objects.filter(user=user).latest('created_at')
        verification.expires_at = timezone.now() - timedelta(minutes=10)
        verification.save()
        
        # Try to verify expired OTP
        response = self.client.post(self.phone_verify_url, {
            'phone': self.test_phone,
            'otp_code': verification.otp_code
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertIn('expired', response.data['message'].lower())
    
    def test_phone_verify_missing_fields(self):
        """Test OTP verification with missing required fields"""
        response = self.client.post(self.phone_verify_url, {
            'phone': self.test_phone
            # Missing otp_code
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
    
    def test_phone_resend_otp(self):
        """Test resending OTP"""
        # Send initial OTP
        self.client.post(self.phone_login_url, {
            'phone': self.test_phone
        })
        
        # Resend OTP
        response = self.client.post(self.phone_resend_url, {
            'phone': self.test_phone
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('resent', response.data['message'].lower())
        
        # Verify new OTP was created
        user = CustomUser.objects.filter(phone=self.test_phone).first()
        verifications = PhoneVerification.objects.filter(user=user).order_by('-created_at')
        self.assertGreaterEqual(verifications.count(), 2)  # At least 2 OTPs
    
    def test_phone_verify_without_name_creates_minimal_user(self):
        """Test that user can be created without name (minimal user)"""
        # Send OTP
        self.client.post(self.phone_login_url, {
            'phone': self.test_phone
        })
        
        # Get OTP
        user = CustomUser.objects.filter(phone=self.test_phone).first()
        verification = PhoneVerification.objects.filter(user=user).latest('created_at')
        
        # Verify without name
        response = self.client.post(self.phone_verify_url, {
            'phone': self.test_phone,
            'otp_code': verification.otp_code
        })
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertIn('tokens', response.data['data'])
        
        # User should exist but without name
        user.refresh_from_db()
        self.assertEqual(user.phone, self.test_phone)
        self.assertTrue(user.phone_verified)
    
    def test_phone_verify_updates_existing_minimal_user(self):
        """Test that providing name updates a minimal user"""
        # Create minimal user (from previous OTP send)
        self.client.post(self.phone_login_url, {
            'phone': self.test_phone
        })
        
        user = CustomUser.objects.filter(phone=self.test_phone).first()
        verification = PhoneVerification.objects.filter(user=user).latest('created_at')
        
        # First verify without name (creates minimal user)
        self.client.post(self.phone_verify_url, {
            'phone': self.test_phone,
            'otp_code': verification.otp_code
        })
        
        # Send new OTP
        self.client.post(self.phone_login_url, {
            'phone': self.test_phone
        })
        
        # Get new OTP
        user.refresh_from_db()
        verification = PhoneVerification.objects.filter(user=user).latest('created_at')
        
        # Verify with name (should update user)
        response = self.client.post(self.phone_verify_url, {
            'phone': self.test_phone,
            'otp_code': verification.otp_code,
            'name': 'Updated Name'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(user.first_name, 'Updated')
        self.assertEqual(user.last_name, 'Name')
    
    def test_phone_unique_constraint(self):
        """Test that phone numbers must be unique"""
        # Create user with phone
        CustomUser.objects.create_user(
            username='user1',
            phone=self.test_phone
        )
        
        # Try to create another user with same phone (should fail at model level)
        with self.assertRaises(Exception):
            CustomUser.objects.create_user(
                username='user2',
                phone=self.test_phone
            )
    
    def test_jwt_tokens_work_after_phone_login(self):
        """Test that JWT tokens from phone login work for authenticated endpoints"""
        # Complete phone login flow
        self.client.post(self.phone_login_url, {
            'phone': self.test_phone
        })
        
        user = CustomUser.objects.filter(phone=self.test_phone).first()
        verification = PhoneVerification.objects.filter(user=user).latest('created_at')
        
        verify_response = self.client.post(self.phone_verify_url, {
            'phone': self.test_phone,
            'otp_code': verification.otp_code,
            'name': 'Test User'
        })
        
        access_token = verify_response.data['data']['tokens']['access_token']
        
        # Use token to access protected endpoint
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        profile_response = self.client.get(reverse('user-profile'))
        
        self.assertEqual(profile_response.status_code, status.HTTP_200_OK)
        self.assertTrue(profile_response.data['success'])

