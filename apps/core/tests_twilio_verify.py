"""
Test cases for Twilio Verify API integration
"""
from django.test import TestCase
from unittest.mock import patch, MagicMock
from django.contrib.auth import get_user_model
from apps.core.models import PhoneVerification
from apps.core.services import PhoneVerificationService
from apps.core.twilio_service import TwilioSMSService
from django.utils import timezone
from datetime import timedelta
from django.conf import settings

User = get_user_model()


class TwilioVerifyServiceTestCase(TestCase):
    """Test cases for Twilio Verify service methods"""
    
    def setUp(self):
        """Set up test data"""
        self.test_phone = '0501234567'
        self.test_phone_formatted = '+966501234567'
        self.real_phone = '0512345678'  # Not in test phones list
        self.real_phone_formatted = '+966512345678'
    
    @patch('apps.core.twilio_service.TWILIO_AVAILABLE', True)
    @patch('apps.core.twilio_service.Client')
    def test_send_verification_code_success(self, mock_client_class):
        """Test successful verification code sending via Twilio Verify"""
        # Mock Twilio client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # Mock verification response
        mock_verification = MagicMock()
        mock_verification.sid = 'VE1234567890abcdef'
        mock_services = MagicMock()
        mock_services.verifications.create.return_value = mock_verification
        mock_client.verify.v2.services.return_value = mock_services
        
        # Set up settings
        with self.settings(
            TWILIO_ACCOUNT_SID='ACtest123',
            TWILIO_AUTH_TOKEN='test_token',
            TWILIO_VERIFY_SERVICE_SID='VAtest123'
        ):
            success, message, verification_sid = TwilioSMSService.send_verification_code(
                phone_number=self.real_phone,
                locale='ar'
            )
        
        self.assertTrue(success)
        self.assertEqual(verification_sid, 'VE1234567890abcdef')
        self.assertIn('sent', message.lower())
    
    def test_send_verification_code_missing_config(self):
        """Test verification code sending with missing Twilio Verify config"""
        # Skip if Twilio SDK not available
        try:
            import twilio
        except ImportError:
            self.skipTest("Twilio SDK not installed")
        
        with self.settings(
            TWILIO_ACCOUNT_SID='ACtest123',
            TWILIO_AUTH_TOKEN='test_token',
            TWILIO_VERIFY_SERVICE_SID=None  # Missing
        ):
            success, message, verification_sid = TwilioSMSService.send_verification_code(
                phone_number=self.real_phone
            )
        
        self.assertFalse(success)
        self.assertIn('TWILIO_VERIFY_SERVICE_SID', message)
        self.assertEqual(verification_sid, '')
    
    @patch('apps.core.twilio_service.TWILIO_AVAILABLE', True)
    @patch('apps.core.twilio_service.Client')
    def test_send_verification_code_twilio_error(self, mock_client_class):
        """Test verification code sending with Twilio API error"""
        from twilio.base.exceptions import TwilioRestException
        
        # Mock Twilio client to raise exception
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_services = MagicMock()
        mock_services.verifications.create.side_effect = TwilioRestException(
            401, 'http://test', 'Unauthorized'
        )
        mock_client.verify.v2.services.return_value = mock_services
        
        with self.settings(
            TWILIO_ACCOUNT_SID='ACtest123',
            TWILIO_AUTH_TOKEN='test_token',
            TWILIO_VERIFY_SERVICE_SID='VAtest123'
        ):
            success, message, verification_sid = TwilioSMSService.send_verification_code(
                phone_number=self.real_phone
            )
        
        self.assertFalse(success)
        self.assertIn('401', message)
        self.assertEqual(verification_sid, '')
    
    @patch('apps.core.twilio_service.TWILIO_AVAILABLE', True)
    @patch('apps.core.twilio_service.Client')
    def test_verify_code_success(self, mock_client_class):
        """Test successful code verification via Twilio Verify"""
        # Mock Twilio client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # Mock verification check response
        mock_verification_check = MagicMock()
        mock_verification_check.status = 'approved'
        mock_services = MagicMock()
        mock_services.verification_checks.create.return_value = mock_verification_check
        mock_client.verify.v2.services.return_value = mock_services
        
        with self.settings(
            TWILIO_ACCOUNT_SID='ACtest123',
            TWILIO_AUTH_TOKEN='test_token',
            TWILIO_VERIFY_SERVICE_SID='VAtest123'
        ):
            is_valid, message = TwilioSMSService.verify_code(
                phone_number=self.real_phone,
                code='123456'
            )
        
        self.assertTrue(is_valid)
        self.assertIn('verified', message.lower())
    
    @patch('apps.core.twilio_service.TWILIO_AVAILABLE', True)
    @patch('apps.core.twilio_service.Client')
    def test_verify_code_invalid(self, mock_client_class):
        """Test code verification with invalid code"""
        # Mock Twilio client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # Mock verification check response with pending status
        mock_verification_check = MagicMock()
        mock_verification_check.status = 'pending'
        mock_services = MagicMock()
        mock_services.verification_checks.create.return_value = mock_verification_check
        mock_client.verify.v2.services.return_value = mock_services
        
        with self.settings(
            TWILIO_ACCOUNT_SID='ACtest123',
            TWILIO_AUTH_TOKEN='test_token',
            TWILIO_VERIFY_SERVICE_SID='VAtest123'
        ):
            is_valid, message = TwilioSMSService.verify_code(
                phone_number=self.real_phone,
                code='999999'
            )
        
        self.assertFalse(is_valid)
        self.assertIn('Invalid', message)
    
    @patch('apps.core.twilio_service.TWILIO_AVAILABLE', True)
    @patch('apps.core.twilio_service.Client')
    def test_verify_code_not_found(self, mock_client_class):
        """Test code verification when verification not found"""
        from twilio.base.exceptions import TwilioRestException
        
        # Mock Twilio client to raise 404 exception
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_services = MagicMock()
        mock_services.verification_checks.create.side_effect = TwilioRestException(
            404, 'http://test', 'Not Found'
        )
        mock_client.verify.v2.services.return_value = mock_services
        
        with self.settings(
            TWILIO_ACCOUNT_SID='ACtest123',
            TWILIO_AUTH_TOKEN='test_token',
            TWILIO_VERIFY_SERVICE_SID='VAtest123'
        ):
            is_valid, message = TwilioSMSService.verify_code(
                phone_number=self.real_phone,
                code='123456'
            )
        
        self.assertFalse(is_valid)
        self.assertIn('not found', message.lower())


class PhoneVerificationServiceTwilioTestCase(TestCase):
    """Test cases for PhoneVerificationService with Twilio Verify integration"""
    
    def setUp(self):
        """Set up test data"""
        self.test_phone = '0500000000'  # Test phone
        self.real_phone = '0512345678'  # Real phone (not in test list)
    
    def test_create_verification_for_test_phone(self):
        """Test that test phones still use fixed OTP"""
        verification, otp_code, sms_success, sms_message, user = PhoneVerificationService.create_verification_for_phone(
            phone_number=self.test_phone
        )
        
        # Test phone should use fixed OTP
        self.assertEqual(otp_code, '123456')
        self.assertTrue(sms_success)
        self.assertIsNotNone(verification)
        self.assertEqual(verification.otp_code, '123456')
        self.assertIsNone(verification.verification_sid)  # Test phones don't use Twilio Verify
        self.assertIsNotNone(user)
    
    @patch('apps.core.twilio_service.TwilioSMSService.send_verification_code')
    def test_create_verification_for_real_phone_success(self, mock_send_verify):
        """Test creating verification for real phone with Twilio Verify"""
        # Mock successful Twilio Verify response
        mock_send_verify.return_value = (True, "Verification code sent successfully", "VE1234567890abcdef")
        
        verification, otp_code, sms_success, sms_message, user = PhoneVerificationService.create_verification_for_phone(
            phone_number=self.real_phone
        )
        
        # Real phone should use Twilio Verify
        self.assertIsNone(otp_code)  # No OTP code stored for Twilio Verify
        self.assertTrue(sms_success)
        self.assertIsNotNone(verification)
        self.assertEqual(verification.verification_sid, 'VE1234567890abcdef')
        self.assertIsNone(verification.otp_code)  # Should be None for Twilio Verify
        self.assertIsNotNone(user)
        
        # Verify Twilio Verify was called
        mock_send_verify.assert_called_once()
        call_args = mock_send_verify.call_args
        # Check phone was formatted (either as first arg or in kwargs)
        phone_arg = call_args[0][0] if call_args[0] else call_args[1].get('phone_number', '')
        self.assertIn('+966', phone_arg)  # Phone should be formatted
    
    @patch('apps.core.twilio_service.TwilioSMSService.send_verification_code')
    def test_create_verification_for_real_phone_failure(self, mock_send_verify):
        """Test creating verification when Twilio Verify fails"""
        # Mock failed Twilio Verify response
        mock_send_verify.return_value = (False, "Twilio Verify not configured", "")
        
        verification, otp_code, sms_success, sms_message, user = PhoneVerificationService.create_verification_for_phone(
            phone_number=self.real_phone
        )
        
        # Should still create verification record for tracking
        self.assertIsNotNone(verification)
        self.assertFalse(sms_success)
        self.assertIsNone(verification.verification_sid)
        self.assertIsNotNone(user)
    
    def test_verify_otp_for_test_phone(self):
        """Test OTP verification for test phone (manual verification)"""
        # Create user and verification
        user = User.objects.create_user(
            username='test_user',
            phone=self.test_phone,
            email=None
        )
        
        verification = PhoneVerification.objects.create(
            user=user,
            phone_number='+966500000000',
            otp_code='123456',
            expires_at=timezone.now() + timedelta(minutes=5)
        )
        
        # Verify OTP
        is_valid, message, verified_user = PhoneVerificationService.verify_otp_for_phone(
            phone_number=self.test_phone,
            otp_code='123456'
        )
        
        self.assertTrue(is_valid)
        self.assertIsNotNone(verified_user)
        self.assertEqual(verified_user.id, user.id)
        
        # Check verification was marked as verified
        verification.refresh_from_db()
        self.assertTrue(verification.is_verified)
        # Refresh user to get updated phone_verified status
        user.refresh_from_db()
        self.assertTrue(user.phone_verified)
    
    @patch('apps.core.twilio_service.TwilioSMSService.verify_code')
    def test_verify_otp_for_real_phone_success(self, mock_verify_code):
        """Test OTP verification for real phone with Twilio Verify"""
        # Create user and verification with Twilio Verify SID
        user = User.objects.create_user(
            username='real_user',
            phone=self.real_phone,
            email=None
        )
        
        verification = PhoneVerification.objects.create(
            user=user,
            phone_number='+966512345678',
            otp_code=None,  # No OTP code for Twilio Verify
            verification_sid='VE1234567890abcdef',
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        
        # Mock successful Twilio Verify
        mock_verify_code.return_value = (True, "Phone verified successfully!")
        
        # Verify OTP
        is_valid, message, verified_user = PhoneVerificationService.verify_otp_for_phone(
            phone_number=self.real_phone,
            otp_code='123456'
        )
        
        self.assertTrue(is_valid)
        self.assertIsNotNone(verified_user)
        self.assertEqual(verified_user.id, user.id)
        
        # Check verification was marked as verified
        verification.refresh_from_db()
        self.assertTrue(verification.is_verified)
        # Refresh user to get updated phone_verified status
        user.refresh_from_db()
        self.assertTrue(user.phone_verified)
        
        # Verify Twilio Verify was called
        mock_verify_code.assert_called_once()
    
    @patch('apps.core.twilio_service.TwilioSMSService.verify_code')
    def test_verify_otp_for_real_phone_invalid_code(self, mock_verify_code):
        """Test OTP verification with invalid code for real phone"""
        # Create user and verification
        user = User.objects.create_user(
            username='real_user',
            phone=self.real_phone,
            email=None
        )
        
        PhoneVerification.objects.create(
            user=user,
            phone_number='+966512345678',
            verification_sid='VE1234567890abcdef',
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        
        # Mock failed Twilio Verify
        mock_verify_code.return_value = (False, "Invalid or expired verification code")
        
        # Verify OTP
        is_valid, message, verified_user = PhoneVerificationService.verify_otp_for_phone(
            phone_number=self.real_phone,
            otp_code='999999'
        )
        
        self.assertFalse(is_valid)
        self.assertIsNone(verified_user)
        self.assertIn('Invalid', message)
    
    def test_verify_otp_user_not_found(self):
        """Test OTP verification when user doesn't exist"""
        is_valid, message, user = PhoneVerificationService.verify_otp_for_phone(
            phone_number='0599999999',  # Non-existent user
            otp_code='123456'
        )
        
        self.assertFalse(is_valid)
        self.assertIsNone(user)
        self.assertIn('not found', message.lower())
    
    def test_create_verification_email_constraint_handling(self):
        """Test that email constraint issues are handled when creating user"""
        # Create a user with empty email string (simulating old data)
        existing_user = User.objects.create_user(
            username='existing',
            phone='0511111111',
            email='',  # Empty string
            is_active=True
        )
        
        # Delete the user but keep the email constraint issue
        existing_user.delete()
        
        # Try to create verification - should handle email constraint
        try:
            verification, otp_code, sms_success, sms_message, user = PhoneVerificationService.create_verification_for_phone(
                phone_number='0511111111'
            )
            # Should succeed after cleanup
            self.assertIsNotNone(user)
        except Exception as e:
            # If it still fails, that's okay - the cleanup should have been attempted
            self.fail(f"Email constraint should have been handled: {e}")


class PhoneVerificationEdgeCasesTestCase(TestCase):
    """Test edge cases and error scenarios"""
    
    def setUp(self):
        """Set up test data"""
        self.test_phone = '0500000000'
        self.real_phone = '0512345678'
    
    def test_verify_expired_test_otp(self):
        """Test verifying expired OTP for test phone"""
        user = User.objects.create_user(
            username='test_user',
            phone=self.test_phone,
            email=None
        )
        
        verification = PhoneVerification.objects.create(
            user=user,
            phone_number='+966500000000',
            otp_code='123456',
            expires_at=timezone.now() - timedelta(minutes=10)  # Expired
        )
        
        is_valid, message, verified_user = PhoneVerificationService.verify_otp_for_phone(
            phone_number=self.test_phone,
            otp_code='123456'
        )
        
        self.assertFalse(is_valid)
        self.assertIsNone(verified_user)
        self.assertIn('expired', message.lower())
    
    def test_verify_already_verified_otp(self):
        """Test verifying an already verified OTP"""
        user = User.objects.create_user(
            username='test_user',
            phone=self.test_phone,
            email=None
        )
        
        verification = PhoneVerification.objects.create(
            user=user,
            phone_number='+966500000000',
            otp_code='123456',
            is_verified=True,  # Already verified
            expires_at=timezone.now() + timedelta(minutes=5)
        )
        
        is_valid, message, verified_user = PhoneVerificationService.verify_otp_for_phone(
            phone_number=self.test_phone,
            otp_code='123456'
        )
        
        self.assertFalse(is_valid)
        self.assertIsNone(verified_user)
    
    def test_multiple_verifications_same_user(self):
        """Test that multiple verifications can exist for same user"""
        user = User.objects.create_user(
            username='test_user',
            phone=self.test_phone,
            email=None
        )
        
        # Create multiple verifications
        verification1 = PhoneVerification.objects.create(
            user=user,
            phone_number='+966500000000',
            otp_code='111111',
            expires_at=timezone.now() + timedelta(minutes=5)
        )
        
        verification2 = PhoneVerification.objects.create(
            user=user,
            phone_number='+966500000000',
            otp_code='222222',
            expires_at=timezone.now() + timedelta(minutes=5)
        )
        
        # Should get the latest one
        is_valid, message, verified_user = PhoneVerificationService.verify_otp_for_phone(
            phone_number=self.test_phone,
            otp_code='222222'  # Latest OTP
        )
        
        self.assertTrue(is_valid)
        self.assertIsNotNone(verified_user)
    
    @patch('apps.core.twilio_service.TwilioSMSService.send_verification_code')
    def test_real_phone_creates_verification_record_on_failure(self, mock_send_verify):
        """Test that verification record is created even if Twilio Verify fails"""
        # Mock failed Twilio Verify
        mock_send_verify.return_value = (False, "Service unavailable", "")
        
        verification, otp_code, sms_success, sms_message, user = PhoneVerificationService.create_verification_for_phone(
            phone_number=self.real_phone
        )
        
        # Verification record should still exist for tracking
        self.assertIsNotNone(verification)
        self.assertFalse(sms_success)
        self.assertIsNotNone(user)
    
    def test_phone_normalization(self):
        """Test phone number normalization for different formats"""
        test_cases = [
            ('0501234567', '0501234567'),  # Standard Saudi
            ('501234567', '0501234567'),   # Without leading 0
            ('+966501234567', '0501234567'),  # E.164 format
            ('966501234567', '0501234567'),   # With country code
        ]
        
        for input_phone, expected_local in test_cases:
            with self.subTest(phone=input_phone):
                local = PhoneVerificationService.normalize_phone_to_local(input_phone)
                self.assertEqual(local, expected_local)
    
    def test_verification_sid_storage(self):
        """Test that verification_sid is properly stored for Twilio Verify"""
        user = User.objects.create_user(
            username='test_user',
            phone=self.real_phone,
            email=None
        )
        
        # Create verification with Twilio Verify SID
        verification = PhoneVerification.objects.create(
            user=user,
            phone_number='+966512345678',
            verification_sid='VE1234567890abcdef',
            otp_code=None,
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        
        self.assertEqual(verification.verification_sid, 'VE1234567890abcdef')
        self.assertIsNone(verification.otp_code)
    
    def test_test_phone_list_comprehensive(self):
        """Test all test phones work correctly"""
        test_phones = ['0500000000', '0510000001', '0599999999', '0511111111', 
                      '0511111112', '0511111113', '0511111114', '0511111115']
        
        for test_phone in test_phones:
            with self.subTest(phone=test_phone):
                # Just test that verification can be created (user may already exist)
                verification, otp_code, sms_success, sms_message, user = PhoneVerificationService.create_verification_for_phone(
                    phone_number=test_phone
                )
                
                self.assertEqual(otp_code, '123456')
                self.assertTrue(sms_success)
                self.assertIsNotNone(verification)
                self.assertIsNotNone(user)

