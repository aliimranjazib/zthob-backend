"""Test cases for Taqnyat Verify API integration."""
from django.test import TestCase
from unittest.mock import patch
from django.contrib.auth import get_user_model
from apps.core.models import PhoneVerification
from apps.core.services import PhoneVerificationService
from apps.core.taqnyat_service import TaqnyatVerifyService, VERIFY_CODE_SENT, VERIFY_SUCCESS, VERIFY_INCORRECT
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class TaqnyatVerifyServiceTestCase(TestCase):
    def setUp(self):
        self.real_phone = '0512345678'
        self.request_id = 'test-request-id-123'

    @patch('apps.core.taqnyat_service.TaqnyatVerifyService._post_verify')
    def test_send_verification_code_success(self, mock_post):
        mock_post.return_value = (True, 'sent', VERIFY_CODE_SENT)

        with self.settings(
            TAQNYAT_BEARER_TOKEN='test_token',
            TAQNYAT_SENDER_NAME='TestSender',
        ):
            success, message = TaqnyatVerifyService.send_verification_code(
                phone_number=self.real_phone,
                request_id=self.request_id,
                lang='ar',
            )

        self.assertTrue(success)
        self.assertIn('sent', message.lower())

    def test_send_verification_code_missing_config(self):
        with self.settings(TAQNYAT_BEARER_TOKEN=None, TAQNYAT_SENDER_NAME=None):
            success, message = TaqnyatVerifyService.send_verification_code(
                phone_number=self.real_phone,
                request_id=self.request_id,
            )

        self.assertFalse(success)
        self.assertIn('TAQNYAT_BEARER_TOKEN', message)

    @patch('apps.core.taqnyat_service.TaqnyatVerifyService._post_verify')
    def test_verify_code_success(self, mock_post):
        mock_post.return_value = (True, 'verified', VERIFY_SUCCESS)

        with self.settings(
            TAQNYAT_BEARER_TOKEN='test_token',
            TAQNYAT_SENDER_NAME='TestSender',
        ):
            is_valid, message = TaqnyatVerifyService.verify_code(
                phone_number=self.real_phone,
                request_id=self.request_id,
                code='1234',
                lang='ar',
            )

        self.assertTrue(is_valid)
        self.assertIn('verified', message.lower())

    @patch('apps.core.taqnyat_service.TaqnyatVerifyService._post_verify')
    def test_verify_code_invalid(self, mock_post):
        mock_post.return_value = (True, 'incorrect', VERIFY_INCORRECT)

        with self.settings(
            TAQNYAT_BEARER_TOKEN='test_token',
            TAQNYAT_SENDER_NAME='TestSender',
        ):
            is_valid, message = TaqnyatVerifyService.verify_code(
                phone_number=self.real_phone,
                request_id=self.request_id,
                code='9999',
            )

        self.assertFalse(is_valid)
        self.assertIn('invalid', message.lower())


class PhoneVerificationServiceTaqnyatTestCase(TestCase):
    def setUp(self):
        self.test_phone = '0500000000'
        self.real_phone = '0512345678'

    def test_create_verification_for_test_phone(self):
        verification, otp_code, sms_success, sms_message, user = (
            PhoneVerificationService.create_verification_for_phone(
                phone_number=self.test_phone
            )
        )

        self.assertEqual(otp_code, '1234')
        self.assertTrue(sms_success)
        self.assertEqual(verification.otp_code, '1234')
        self.assertIsNone(verification.verification_sid)
        self.assertIsNotNone(user)

    @patch('apps.core.tasks.send_verification_code_task.delay')
    def test_create_verification_for_real_phone(self, mock_delay):
        verification, otp_code, sms_success, sms_message, user = (
            PhoneVerificationService.create_verification_for_phone(
                phone_number=self.real_phone
            )
        )

        self.assertIsNone(otp_code)
        self.assertTrue(sms_success)
        self.assertIsNotNone(verification.verification_sid)
        self.assertIsNone(verification.otp_code)
        mock_delay.assert_called_once()

    def test_verify_otp_for_test_phone(self):
        user = User.objects.create_user(
            username='test_user',
            phone=self.test_phone,
            email=None,
        )

        verification = PhoneVerification.objects.create(
            user=user,
            phone_number='+966500000000',
            otp_code='1234',
            expires_at=timezone.now() + timedelta(minutes=5),
        )

        is_valid, message, verified_user = PhoneVerificationService.verify_otp_for_phone(
            phone_number=self.test_phone,
            otp_code='1234',
        )

        self.assertTrue(is_valid)
        self.assertEqual(verified_user.id, user.id)
        verification.refresh_from_db()
        self.assertTrue(verification.is_verified)

    @patch('apps.core.taqnyat_service.TaqnyatVerifyService.verify_code')
    def test_verify_otp_for_real_phone_success(self, mock_verify):
        user = User.objects.create_user(
            username='real_user',
            phone=self.real_phone,
            email=None,
        )

        verification = PhoneVerification.objects.create(
            user=user,
            phone_number='+966512345678',
            otp_code=None,
            verification_sid='request-id-abc',
            expires_at=timezone.now() + timedelta(minutes=10),
        )

        mock_verify.return_value = (True, 'Phone verified successfully!')

        is_valid, message, verified_user = PhoneVerificationService.verify_otp_for_phone(
            phone_number=self.real_phone,
            otp_code='1234',
        )

        self.assertTrue(is_valid)
        self.assertEqual(verified_user.id, user.id)
        verification.refresh_from_db()
        self.assertTrue(verification.is_verified)
        mock_verify.assert_called_once()

    @patch('apps.core.taqnyat_service.TaqnyatVerifyService.verify_code')
    def test_verify_otp_for_real_phone_invalid_code(self, mock_verify):
        user = User.objects.create_user(
            username='real_user',
            phone=self.real_phone,
            email=None,
        )

        PhoneVerification.objects.create(
            user=user,
            phone_number='+966512345678',
            verification_sid='request-id-abc',
            expires_at=timezone.now() + timedelta(minutes=10),
        )

        mock_verify.return_value = (False, 'Invalid or expired verification code')

        is_valid, message, verified_user = PhoneVerificationService.verify_otp_for_phone(
            phone_number=self.real_phone,
            otp_code='9999',
        )

        self.assertFalse(is_valid)
        self.assertIsNone(verified_user)

    def test_verify_otp_user_not_found(self):
        is_valid, message, user = PhoneVerificationService.verify_otp_for_phone(
            phone_number='0599999999',
            otp_code='1234',
        )

        self.assertFalse(is_valid)
        self.assertIsNone(user)

    def test_phone_normalization(self):
        test_cases = [
            ('0501234567', '0501234567'),
            ('501234567', '0501234567'),
            ('+966501234567', '0501234567'),
            ('966501234567', '0501234567'),
        ]

        for input_phone, expected_local in test_cases:
            with self.subTest(phone=input_phone):
                local = PhoneVerificationService.normalize_phone_to_local(input_phone)
                self.assertEqual(local, expected_local)
