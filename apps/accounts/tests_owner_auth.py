"""Tests for owner-side authentication endpoints."""

from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import CustomUser
from apps.core.services import PhoneVerificationService
from apps.tailors.models import TailorEmployee, TailorProfile

TEST_REST_FRAMEWORK = {
    **settings.REST_FRAMEWORK,
    'DEFAULT_THROTTLE_CLASSES': [],
}


@override_settings(REST_FRAMEWORK=TEST_REST_FRAMEWORK)
class OwnerAuthenticationTestCase(TestCase):
    def setUp(self):
        from apps.accounts import views as account_views
        from apps.accounts import views_owner as owner_views

        self._saved_throttles = (
            account_views.PhoneLoginView.throttle_classes,
            account_views.PhoneVerifyView.throttle_classes,
            account_views.PhoneResendOTPView.throttle_classes,
            owner_views.OwnerPhoneVerifyView.throttle_classes,
        )
        account_views.PhoneLoginView.throttle_classes = []
        account_views.PhoneVerifyView.throttle_classes = []
        account_views.PhoneResendOTPView.throttle_classes = []
        owner_views.OwnerPhoneVerifyView.throttle_classes = []

        self.client = APIClient()
        self.phone_login_url = reverse('accounts:phone-login')
        self.phone_verify_url = reverse('accounts:phone-verify')
        self.owner_verify_url = reverse('accounts:owner-phone-verify')
        self.owner_switch_url = reverse('accounts:owner-switch-shop')
        self.owner_context_url = reverse('accounts:owner-auth-context')
        self.test_phone = '0500000001'
        self.test_otp = PhoneVerificationService.TEST_OTP

    def tearDown(self):
        from apps.accounts import views as account_views
        from apps.accounts import views_owner as owner_views

        (
            account_views.PhoneLoginView.throttle_classes,
            account_views.PhoneVerifyView.throttle_classes,
            account_views.PhoneResendOTPView.throttle_classes,
            owner_views.OwnerPhoneVerifyView.throttle_classes,
        ) = self._saved_throttles

    def _owner_login(self, *, name='Owner User'):
        self.client.post(self.phone_login_url, {'phone': self.test_phone})
        return self.client.post(self.owner_verify_url, {
            'phone': self.test_phone,
            'otp_code': self.test_otp,
            'name': name,
        })

    def test_legacy_phone_verify_unchanged_without_app_entry(self):
        self.client.post(self.phone_login_url, {'phone': self.test_phone})
        response = self.client.post(self.phone_verify_url, {
            'phone': self.test_phone,
            'otp_code': self.test_otp,
            'name': 'Legacy User',
            'role': 'USER',
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        tailor_context = response.data['data']['tailor_context']
        self.assertEqual(
            set(tailor_context.keys()),
            {'is_owner', 'is_employee', 'shop_id', 'roles', 'permissions'},
        )
        access_token = response.data['data']['tokens']['access_token']
        self.assertNotIn('shop_id', self._decode_jwt_payload(access_token))

    def test_owner_phone_verify_returns_owner_context(self):
        response = self._owner_login()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.data['data']
        context = data['tailor_context']

        self.assertEqual(context['app_entry'], 'owner')
        self.assertEqual(context['mode'], 'owner')
        self.assertEqual(context['access_mode'], 'owner')
        self.assertEqual(context['routing']['initial_screen'], 'owner_dashboard')
        self.assertIn('owned_shops', context)
        self.assertIn('assigned_shops', context)
        self.assertFalse(context['can_enter_shop_work'])

    def test_owner_with_shop_can_switch_shop(self):
        response = self._owner_login()
        user = CustomUser.objects.get(phone=self.test_phone)
        profile = user.tailor_profile
        profile.shop_name = 'Owner Shop'
        profile.save(update_fields=['shop_name'])

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {response.data['data']['tokens']['access_token']}"
        )
        switch_response = self.client.post(self.owner_switch_url, {'shop_id': profile.id})

        self.assertEqual(switch_response.status_code, status.HTTP_200_OK)
        context = switch_response.data['data']['tailor_context']
        self.assertEqual(context['active_shop_id'], profile.id)
        self.assertEqual(context['routing']['initial_screen'], 'shop_work')

        payload = self._decode_jwt_payload(
            switch_response.data['data']['tokens']['access_token']
        )
        self.assertEqual(payload['shop_id'], profile.id)
        self.assertEqual(payload['access_mode'], 'owner')
        self.assertEqual(payload['app_entry'], 'owner')

    def test_owner_context_endpoint(self):
        response = self._owner_login()
        token = response.data['data']['tokens']['access_token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        context_response = self.client.get(self.owner_context_url)
        self.assertEqual(context_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            context_response.data['data']['tailor_context']['app_entry'],
            'owner',
        )

    def test_switch_shop_denied_for_unrelated_user(self):
        owner_response = self._owner_login()
        owner = CustomUser.objects.get(phone=self.test_phone)
        owner_profile = owner.tailor_profile
        owner_profile.shop_name = 'Owner Shop'
        owner_profile.save(update_fields=['shop_name'])

        other = CustomUser.objects.create_user(
            username='other_owner',
            phone='0500000002',
            role='TAILOR',
        )
        other_profile = other.tailor_profile
        other_profile.shop_name = 'Other Shop'
        other_profile.save(update_fields=['shop_name'])

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {owner_response.data['data']['tokens']['access_token']}"
        )
        denied = self.client.post(self.owner_switch_url, {'shop_id': other_profile.id})
        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)

    def test_employee_can_switch_assigned_shop(self):
        owner = CustomUser.objects.create_user(
            username='shop_owner',
            phone='0522222220',
            role='TAILOR',
        )
        shop = owner.tailor_profile
        shop.shop_name = 'Assigned Shop'
        shop.save(update_fields=['shop_name'])

        employee_user = CustomUser.objects.create_user(
            username='employee_user',
            phone='0522222221',
            role='TAILOR',
        )
        TailorEmployee.objects.create(
            tailor=shop,
            user=employee_user,
            roles=['stitcher'],
            can_stitch_orders=True,
        )

        self.client.post(self.phone_login_url, {'phone': employee_user.phone})
        login = self.client.post(self.owner_verify_url, {
            'phone': employee_user.phone,
            'otp_code': self.test_otp,
        })
        self.assertIn(login.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED))

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login.data['data']['tokens']['access_token']}"
        )
        switch_response = self.client.post(self.owner_switch_url, {'shop_id': shop.id})
        self.assertEqual(switch_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            switch_response.data['data']['tailor_context']['access_mode'],
            'employee',
        )

    @staticmethod
    def _decode_jwt_payload(access_token):
        import base64
        import json

        payload_segment = access_token.split('.')[1]
        padding = '=' * (-len(payload_segment) % 4)
        decoded = base64.urlsafe_b64decode(payload_segment + padding)
        return json.loads(decoded)
