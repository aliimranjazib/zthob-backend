"""Tests for hardened OTP verification sessions."""

from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.core.models import PhoneVerification
from apps.core.otp_session import OtpErrorCode
from apps.core.services import PhoneVerificationService

User = get_user_model()


@override_settings(REST_FRAMEWORK={
    **__import__('django.conf', fromlist=['settings']).settings.REST_FRAMEWORK,
    'DEFAULT_THROTTLE_CLASSES': [],
})
class OtpSessionHardeningTestCase(TestCase):
    def setUp(self):
        from apps.accounts import views as account_views

        self._saved = (
            account_views.PhoneLoginView.throttle_classes,
            account_views.PhoneVerifyView.throttle_classes,
            account_views.PhoneResendOTPView.throttle_classes,
        )
        account_views.PhoneLoginView.throttle_classes = []
        account_views.PhoneVerifyView.throttle_classes = []
        account_views.PhoneResendOTPView.throttle_classes = []

        self.client = APIClient()
        self.phone_login_url = reverse('accounts:phone-login')
        self.phone_verify_url = reverse('accounts:phone-verify')
        self.phone_resend_url = reverse('accounts:phone-resend-otp')
        self.test_phone = '0500000000'

    def tearDown(self):
        from apps.accounts import views as account_views

        (
            account_views.PhoneLoginView.throttle_classes,
            account_views.PhoneVerifyView.throttle_classes,
            account_views.PhoneResendOTPView.throttle_classes,
        ) = self._saved

    def test_phone_login_returns_verification_session(self):
        response = self.client.post(self.phone_login_url, {'phone': self.test_phone})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data['data']
        self.assertIn('verification_id', data)
        self.assertIn('expires_in', data)
        self.assertIn('resend_after', data)
        self.assertEqual(data['otp_length'], 4)

    def test_new_login_invalidates_previous_session(self):
        first = self.client.post(self.phone_login_url, {'phone': self.test_phone})
        first_id = first.data['data']['verification_id']

        second = self.client.post(self.phone_login_url, {'phone': self.test_phone})
        second_id = second.data['data']['verification_id']
        self.assertNotEqual(first_id, second_id)

        first_session = PhoneVerification.objects.get(session_id=first_id)
        self.assertIsNotNone(first_session.invalidated_at)

        verify_old = self.client.post(
            self.phone_verify_url,
            {
                'verification_id': first_id,
                'otp_code': PhoneVerificationService.TEST_OTP,
                'role': 'USER',
            },
        )
        self.assertEqual(verify_old.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(verify_old.data['errors'], OtpErrorCode.SESSION_NOT_FOUND)

    def test_verify_with_verification_id_success(self):
        login = self.client.post(self.phone_login_url, {'phone': self.test_phone})
        verification_id = login.data['data']['verification_id']

        verify = self.client.post(
            self.phone_verify_url,
            {
                'verification_id': verification_id,
                'otp_code': PhoneVerificationService.TEST_OTP,
                'role': 'USER',
            },
        )
        self.assertIn(verify.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED))
        self.assertTrue(verify.data['success'])
        self.assertIn('tokens', verify.data['data'])

    def test_wrong_otp_returns_otp_invalid(self):
        login = self.client.post(self.phone_login_url, {'phone': self.test_phone})
        verification_id = login.data['data']['verification_id']

        verify = self.client.post(
            self.phone_verify_url,
            {
                'verification_id': verification_id,
                'otp_code': '9999',
                'role': 'USER',
            },
        )
        self.assertEqual(verify.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(verify.data['errors'], OtpErrorCode.INVALID)

    def test_expired_otp_returns_otp_expired(self):
        login = self.client.post(self.phone_login_url, {'phone': self.test_phone})
        verification_id = login.data['data']['verification_id']
        session = PhoneVerification.objects.get(session_id=verification_id)
        session.expires_at = timezone.now() - timedelta(minutes=1)
        session.save(update_fields=['expires_at'])

        verify = self.client.post(
            self.phone_verify_url,
            {
                'verification_id': verification_id,
                'otp_code': PhoneVerificationService.TEST_OTP,
                'role': 'USER',
            },
        )
        self.assertEqual(verify.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(verify.data['errors'], OtpErrorCode.EXPIRED)

    def test_resend_enforces_cooldown(self):
        self.client.post(self.phone_login_url, {'phone': self.test_phone})
        resend = self.client.post(self.phone_resend_url, {'phone': self.test_phone})

        self.assertEqual(resend.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(resend.data['errors'], OtpErrorCode.RESEND_COOLDOWN)
        self.assertIn('verification_id', resend.data['data'])

    @patch('apps.core.tasks.send_verification_code_task.delay')
    def test_backward_compatible_phone_verify_still_works(self, _mock_delay):
        real_phone = '0512345678'
        user = User.objects.create_user(username='legacy_user', phone=real_phone, email=None)
        PhoneVerification.objects.create(
            user=user,
            phone_number='+966512345678',
            verification_sid='legacy-request-id',
            expires_at=timezone.now() + timedelta(minutes=5),
        )

        with patch('apps.core.taqnyat_service.TaqnyatVerifyService.verify_code', return_value=(True, 'ok')):
            verify = self.client.post(
                self.phone_verify_url,
                {'phone': real_phone, 'otp_code': '1234', 'role': 'USER'},
            )

        self.assertIn(verify.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED))
        self.assertTrue(verify.data['success'])
