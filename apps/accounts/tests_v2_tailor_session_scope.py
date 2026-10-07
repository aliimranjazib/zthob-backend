"""
Session-scoped app_entry: solo tailor vs owner JWT and /v2/me payloads.

Run:
  uv run python manage.py test apps.accounts.tests_v2_tailor_session_scope -v 2
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.core.services import PhoneVerificationService
from apps.tailors.models import TailorProfile

User = get_user_model()

TEST_REST_FRAMEWORK = {
    **settings.REST_FRAMEWORK,
    'DEFAULT_THROTTLE_CLASSES': [],
}


@override_settings(
    REST_FRAMEWORK=TEST_REST_FRAMEWORK,
    SECURE_SSL_REDIRECT=False,
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    },
)
class V2TailorSessionScopeTest(TestCase):
    TEST_OTP = PhoneVerificationService.TEST_OTP
    # Must be entries in PhoneVerificationService.TEST_PHONES (fixed OTP 1234).
    SOLO_SHOP_PHONE = '0500000005'
    REAUTH_PHONE = '0500000006'
    PROFILE_PHONE = '0500000007'

    def _unique_phone(self):
        return self.SOLO_SHOP_PHONE

    def setUp(self):
        from apps.accounts import views as account_views

        self._saved_throttles = (
            account_views.PhoneLoginView.throttle_classes,
            account_views.PhoneVerifyView.throttle_classes,
        )
        account_views.PhoneLoginView.throttle_classes = []
        account_views.PhoneVerifyView.throttle_classes = []

        self.client = APIClient()
        self.v2_login_url = reverse('v2:accounts_v2:v2-phone-login')
        self.v2_verify_url = reverse('v2:accounts_v2:v2-phone-verify')
        self.v2_me_url = reverse('v2:accounts_v2:v2-me')
        self.owner_shops_url = reverse('owner-shops')

    def tearDown(self):
        from apps.accounts import views as account_views

        (
            account_views.PhoneLoginView.throttle_classes,
            account_views.PhoneVerifyView.throttle_classes,
        ) = self._saved_throttles

    def _send_otp(self, phone):
        response = self.client.post(self.v2_login_url, {'phone': phone})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def _verify(self, phone, *, app_entry=None, name='Session Test User'):
        payload = {
            'phone': phone,
            'otp_code': self.TEST_OTP,
            'name': name,
            'role': 'TAILOR',
        }
        if app_entry is not None:
            payload['app_entry'] = app_entry
        return self.client.post(self.v2_verify_url, payload)

    def _auth(self, access_token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

    def _create_solo_tailor_with_shop(self, phone=None):
        phone = phone or self._unique_phone()
        self._send_otp(phone)
        verify = self._verify(phone, app_entry='tailor', name='Solo With Shop')
        self.assertIn(
            verify.status_code,
            [status.HTTP_200_OK, status.HTTP_201_CREATED],
            verify.data,
        )
        token = verify.data['data']['tokens']['access_token']
        self._auth(token)
        user = User.objects.get(
            phone=PhoneVerificationService.normalize_phone_to_local(phone),
        )
        profile, _ = TailorProfile.objects.get_or_create(
            owner=user,
            user=user,
            defaults={},
        )
        profile.shop_name = 'Solo Legacy Shop'
        profile.contact_number = phone
        profile.address = 'Riyadh'
        profile.save(update_fields=['shop_name', 'contact_number', 'address'])
        return token, user

    def test_tailor_app_entry_me_after_named_shop(self):
        token, _user = self._create_solo_tailor_with_shop()
        self._auth(token)
        me = self.client.get(
            self.v2_me_url,
            {'app_entry': 'tailor'},
            HTTP_X_APP_ENTRY='tailor',
        )
        self.assertEqual(me.status_code, status.HTTP_200_OK)
        data = me.data['data']
        self.assertEqual(data['membership']['type'], 'tailor')
        self.assertIsNone(data['membership']['business']['id'])
        self.assertFalse(data['permissions']['can_manage_staff'])
        self.assertFalse(data['permissions']['can_manage_business'])
        self.assertIn('platform', data)
        self.assertTrue(data['platform']['owns_shop'])
        self.assertFalse(data['platform']['owner_console_enabled'])

    def test_tailor_jwt_cannot_access_v2_business(self):
        token, _user = self._create_solo_tailor_with_shop()
        self._auth(token)
        business_url = reverse('v2:tailors_v2:v2-business')
        response = self.client.get(business_url, HTTP_X_APP_ENTRY='tailor')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_tailor_jwt_cannot_list_owner_shops(self):
        token, _user = self._create_solo_tailor_with_shop()
        self._auth(token)
        response = self.client.get(self.owner_shops_url, HTTP_X_APP_ENTRY='owner')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_reauth_unlocks_owner_shops(self):
        phone = self.REAUTH_PHONE
        self._create_solo_tailor_with_shop(phone=phone)
        self.client.credentials()
        self._send_otp(phone)
        owner_verify = self._verify(
            phone,
            app_entry='owner',
            name='Solo Upgraded Owner',
        )
        self.assertEqual(owner_verify.status_code, status.HTTP_200_OK)
        owner_token = owner_verify.data['data']['tokens']['access_token']
        self._auth(owner_token)
        me = self.client.get(self.v2_me_url, {'app_entry': 'owner'})
        self.assertEqual(me.status_code, status.HTTP_200_OK)
        self.assertEqual(me.data['data']['membership']['type'], 'owner')
        self.assertTrue(me.data['data']['permissions']['can_manage_staff'])
        self.assertTrue(me.data['data']['platform']['owner_console_enabled'])
        shops = self.client.get(self.owner_shops_url)
        self.assertEqual(shops.status_code, status.HTTP_200_OK)

    def test_accounts_profile_platform_fields_for_tailor_session(self):
        token, _user = self._create_solo_tailor_with_shop(phone=self.PROFILE_PHONE)
        self._auth(token)
        profile_url = reverse('accounts:user-profile')
        response = self.client.get(profile_url, HTTP_X_APP_ENTRY='tailor')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ctx = response.data['data']['tailor_context']
        self.assertEqual(ctx.get('platform_entry'), 'tailor')
        self.assertFalse(ctx.get('show_owner_console'))
        self.assertTrue(ctx.get('owns_shop'))
        self.assertTrue(ctx.get('is_owner'))
