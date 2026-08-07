from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts import views as account_views
from apps.core.models import PhoneVerification
from apps.core.services import PhoneVerificationService
from apps.customers.models import CustomerProfile
from apps.customers.services.welcome_sms import (
    CUSTOMER_WELCOME_SMS_BODY,
    queue_customer_welcome_sms,
    send_customer_welcome_sms,
    should_send_welcome_sms,
)
from apps.tailors.models import TailorProfile

User = get_user_model()


@override_settings(
    SECURE_SSL_REDIRECT=False,
    TAQNYAT_BEARER_TOKEN='test_token',
    TAQNYAT_SENDER_NAME='TestSender',
    REST_FRAMEWORK={
        **__import__('django.conf', fromlist=['settings']).settings.REST_FRAMEWORK,
        'DEFAULT_THROTTLE_CLASSES': [],
    },
)
class CustomerWelcomeSmsServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='welcome_customer',
            phone='0501234567',
            role='USER',
            phone_verified=True,
        )
        self.profile = CustomerProfile.objects.create(user=self.user)

    def test_should_send_welcome_sms_when_not_sent(self):
        self.assertTrue(should_send_welcome_sms(self.profile))

    def test_should_not_send_when_already_sent(self):
        self.profile.welcome_sms_sent_at = timezone.now()
        self.profile.save(update_fields=['welcome_sms_sent_at'])
        self.assertFalse(should_send_welcome_sms(self.profile))

    @patch('apps.customers.services.welcome_sms.TaqnyatSMSService.send_sms')
    def test_send_customer_welcome_sms_success(self, mock_send_sms):
        mock_send_sms.return_value = (True, 'ok', 'msg-123')

        result = send_customer_welcome_sms(self.user.id)

        self.assertTrue(result)
        self.profile.refresh_from_db()
        self.assertIsNotNone(self.profile.welcome_sms_sent_at)
        mock_send_sms.assert_called_once()
        self.assertEqual(mock_send_sms.call_args[0][1], CUSTOMER_WELCOME_SMS_BODY)

    @patch('apps.customers.services.welcome_sms.TaqnyatSMSService.send_sms')
    def test_send_customer_welcome_sms_skips_duplicate(self, mock_send_sms):
        self.profile.welcome_sms_sent_at = timezone.now()
        self.profile.save(update_fields=['welcome_sms_sent_at'])

        result = send_customer_welcome_sms(self.user.id)

        self.assertFalse(result)
        mock_send_sms.assert_not_called()

    @patch('apps.customers.tasks.send_customer_welcome_sms_task.delay')
    def test_queue_customer_welcome_sms(self, mock_delay):
        queue_customer_welcome_sms(self.user.id)
        mock_delay.assert_called_once_with(self.user.id)

    @patch('apps.customers.tasks.send_customer_welcome_sms_task.delay')
    def test_queue_skips_when_already_sent(self, mock_delay):
        self.profile.welcome_sms_sent_at = timezone.now()
        self.profile.save(update_fields=['welcome_sms_sent_at'])

        queue_customer_welcome_sms(self.user.id)
        mock_delay.assert_not_called()


@override_settings(
    SECURE_SSL_REDIRECT=False,
    REST_FRAMEWORK={
        **__import__('django.conf', fromlist=['settings']).settings.REST_FRAMEWORK,
        'DEFAULT_THROTTLE_CLASSES': [],
    },
)
class CustomerWelcomeSmsPhoneVerifyTest(TestCase):
    def setUp(self):
        account_views.PhoneLoginView.throttle_classes = []
        account_views.PhoneVerifyView.throttle_classes = []
        self.client = APIClient()
        self.phone_login_url = reverse('accounts:phone-login')
        self.phone_verify_url = reverse('accounts:phone-verify')
        self.test_phone = '0500000001'

    def tearDown(self):
        account_views.PhoneLoginView.throttle_classes = account_views.PhoneLoginView.throttle_classes or []
        account_views.PhoneVerifyView.throttle_classes = account_views.PhoneVerifyView.throttle_classes or []

    def _verify_new_user(self):
        self.client.post(self.phone_login_url, {'phone': self.test_phone})
        user = User.objects.get(phone=self.test_phone)
        verification = PhoneVerification.objects.filter(user=user).latest('created_at')
        return self.client.post(
            self.phone_verify_url,
            {
                'phone': self.test_phone,
                'otp_code': PhoneVerificationService.TEST_OTP,
                'name': 'New Customer',
                'role': 'USER',
            },
        )

    @patch('apps.customers.services.welcome_sms.queue_customer_welcome_sms')
    def test_app_new_user_triggers_welcome_sms(self, mock_queue):
        response = self._verify_new_user()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['data']['is_new_user'])
        mock_queue.assert_called_once()

    @patch('apps.customers.services.welcome_sms.queue_customer_welcome_sms')
    def test_app_returning_login_does_not_trigger_welcome_sms(self, mock_queue):
        self._verify_new_user()
        mock_queue.reset_mock()

        self.client.post(self.phone_login_url, {'phone': self.test_phone})
        user = User.objects.get(phone=self.test_phone)
        verification = PhoneVerification.objects.filter(user=user).latest('created_at')
        response = self.client.post(
            self.phone_verify_url,
            {
                'phone': self.test_phone,
                'otp_code': PhoneVerificationService.TEST_OTP,
                'role': 'USER',
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['data']['is_new_user'])
        mock_queue.assert_not_called()

    @patch('apps.customers.services.welcome_sms.queue_customer_welcome_sms')
    def test_deleted_account_re_register_does_not_trigger_welcome_sms(self, mock_queue):
        user = User.objects.create_user(
            username='deleted_customer',
            phone=self.test_phone,
            role='USER',
            phone_verified=True,
            is_deleted=True,
            is_active=False,
        )
        CustomerProfile.objects.create(user=user)

        self.client.post(self.phone_login_url, {'phone': self.test_phone})
        verification = PhoneVerification.objects.filter(user=user).latest('created_at')
        response = self.client.post(
            self.phone_verify_url,
            {
                'phone': self.test_phone,
                'otp_code': PhoneVerificationService.TEST_OTP,
                'name': 'Returning Customer',
                'role': 'USER',
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['data']['is_new_user'])
        mock_queue.assert_not_called()


@override_settings(SECURE_SSL_REDIRECT=False)
class CustomerWelcomeSmsPosTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.tailor_user = User.objects.create_user(
            username='pos_tailor_welcome',
            phone='+966500000011',
            role='TAILOR',
        )
        self.tailor_profile, _ = TailorProfile.objects.get_or_create(user=self.tailor_user)
        self.tailor_profile.shop_status = True
        self.tailor_profile.save(update_fields=['shop_status'])
        self.client.force_authenticate(user=self.tailor_user)
        self.create_url = '/api/tailors/pos/customers/create/'

    @patch('apps.customers.services.welcome_sms.queue_customer_welcome_sms')
    def test_pos_new_customer_triggers_welcome_sms(self, mock_queue):
        response = self.client.post(
            self.create_url,
            {'phone': '966500000012', 'name': 'POS Welcome Customer'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(response.data['data']['is_existing'])
        mock_queue.assert_called_once_with(response.data['data']['id'])

    @patch('apps.customers.services.welcome_sms.queue_customer_welcome_sms')
    def test_pos_existing_customer_does_not_trigger_welcome_sms(self, mock_queue):
        existing = User.objects.create_user(
            username='966500000013',
            phone='966500000013',
            role='USER',
        )
        CustomerProfile.objects.create(user=existing)

        response = self.client.post(
            self.create_url,
            {'phone': '966500000013', 'name': 'Existing POS Customer'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['data']['is_existing'])
        mock_queue.assert_not_called()
