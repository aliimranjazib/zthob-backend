"""
V2 auth entry auto-detection: account_status on login, app_entry inference on verify.

Run:
  uv run python manage.py test apps.accounts.tests_v2_auth_entry -v 2
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.services.v2_auth import resolve_v2_app_entry
from apps.core.services import PhoneVerificationService
from apps.tailors.models import Business, TailorProfile, TailorStaffMember
from apps.tailors.services.owner_staff import (
    create_or_update_shop_assignment,
    find_or_create_staff_user,
)


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
class V2AuthEntryFlowTest(TestCase):
    TEST_OTP = PhoneVerificationService.TEST_OTP

    FRESH_PHONE = '0511111111'
    OWNER_PHONE = '0511111112'
    STAFF_PHONE = '0511111113'
    TAILOR_PHONE = '0511111114'
    V1_PHONE = '0511111115'

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
        self.v1_login_url = reverse('accounts:phone-login')

    def tearDown(self):
        from apps.accounts import views as account_views

        (
            account_views.PhoneLoginView.throttle_classes,
            account_views.PhoneVerifyView.throttle_classes,
        ) = self._saved_throttles

    def _send_otp(self, phone):
        return self.client.post(self.v2_login_url, {'phone': phone})

    def _verify(self, phone, *, app_entry=None, name='Auth Entry User'):
        payload = {
            'phone': phone,
            'otp_code': self.TEST_OTP,
            'name': name,
            'role': 'TAILOR',
        }
        if app_entry is not None:
            payload['app_entry'] = app_entry
        return self.client.post(self.v2_verify_url, payload)

    def _login_and_verify(self, phone, *, app_entry=None, name='Auth Entry User'):
        self._send_otp(phone)
        return self._verify(phone, app_entry=app_entry, name=name)

    def _create_owner_with_business(self, phone):
        local_phone = PhoneVerificationService.normalize_phone_to_local(phone)
        user = User.objects.create_user(
            username=f'owner_{local_phone}',
            phone=local_phone,
            role='TAILOR',
            first_name='Owner',
            last_name='User',
        )
        Business.objects.create(
            owner=user,
            name='Existing Business',
            contact_phone=phone,
            city='Riyadh',
            is_active=True,
        )
        return user

    def _create_solo_tailor(self, phone):
        verify = self._login_and_verify(phone, app_entry='tailor', name='Solo Tailor')
        self.assertEqual(verify.status_code, status.HTTP_201_CREATED)
        return verify

    def _create_preinvited_staff(self, *, owner, shop, staff_phone):
        staff_user, _ = find_or_create_staff_user(
            phone=staff_phone,
            name='Pre Invited Staff',
        )
        staff_member, _ = TailorStaffMember.objects.get_or_create(
            owner=owner,
            user=staff_user,
            defaults={'is_active': True},
        )
        create_or_update_shop_assignment(
            staff_member=staff_member,
            shop=shop,
            roles=['manager'],
            permissions=['can_manage_orders'],
            is_active=True,
        )
        return staff_user

    def _create_owner_shop(self, owner, phone):
        profile, _ = TailorProfile.objects.get_or_create(
            owner=owner,
            user=owner,
            defaults={},
        )
        profile.shop_name = 'Existing Shop'
        profile.contact_number = phone
        profile.address = 'Riyadh'
        profile.save(update_fields=['shop_name', 'contact_number', 'address'])
        return profile

    def test_fresh_phone_login_returns_new(self):
        response = self._send_otp(self.FRESH_PHONE)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['account_status'], 'new')

    def test_fresh_phone_verify_without_app_entry_returns_400(self):
        self._send_otp(self.FRESH_PHONE)
        response = self._verify(self.FRESH_PHONE)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('app_entry', response.data['errors'])

    def test_resolve_v2_app_entry_requires_app_entry_for_greenfield(self):
        user = User.objects.create_user(
            username='greenfield_user',
            phone='0511111177',
            role='TAILOR',
        )
        from rest_framework import serializers

        with self.assertRaises(serializers.ValidationError) as ctx:
            resolve_v2_app_entry(
                user,
                requested_app_entry=None,
                membership_before='none',
            )
        self.assertIn('app_entry', ctx.exception.detail)

    def test_fresh_phone_register_as_owner(self):
        login = self._send_otp(self.FRESH_PHONE)
        self.assertEqual(login.data['data']['account_status'], 'new')

        verify = self._verify(self.FRESH_PHONE, app_entry='owner', name='New Owner')
        self.assertEqual(verify.status_code, status.HTTP_201_CREATED)
        self.assertEqual(verify.data['data']['app_entry'], 'owner')
        self.assertEqual(verify.data['data']['app_entry_source'], 'request')
        self.assertTrue(verify.data['data']['is_new_user'])

    def test_fresh_phone_register_as_tailor(self):
        login = self._send_otp(self.TAILOR_PHONE)
        self.assertEqual(login.data['data']['account_status'], 'new')

        verify = self._verify(self.TAILOR_PHONE, app_entry='tailor', name='New Tailor')
        self.assertEqual(verify.status_code, status.HTTP_201_CREATED)
        self.assertEqual(verify.data['data']['app_entry'], 'tailor')

    def test_fresh_phone_cannot_self_register_as_staff(self):
        self._send_otp(self.STAFF_PHONE)
        response = self._verify(self.STAFF_PHONE, app_entry='staff', name='Bad Staff')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_existing_owner_login_and_infer_app_entry(self):
        self._create_owner_with_business(self.OWNER_PHONE)

        login = self._send_otp(self.OWNER_PHONE)
        self.assertEqual(login.data['data']['account_status'], 'existing')

        verify = self._verify(self.OWNER_PHONE, name='Existing Owner')
        self.assertEqual(verify.status_code, status.HTTP_200_OK)
        self.assertEqual(verify.data['data']['app_entry'], 'owner')
        self.assertEqual(verify.data['data']['app_entry_source'], 'inferred')
        self.assertFalse(verify.data['data']['is_new_user'])

    def test_preinvited_staff_login_and_infer_app_entry(self):
        owner = self._create_owner_with_business(self.OWNER_PHONE)
        shop = self._create_owner_shop(owner, self.OWNER_PHONE)
        self._create_preinvited_staff(
            owner=owner,
            shop=shop,
            staff_phone=self.STAFF_PHONE,
        )

        login = self._send_otp(self.STAFF_PHONE)
        self.assertEqual(login.data['data']['account_status'], 'existing')

        verify = self._verify(self.STAFF_PHONE, name='Staff Member')
        self.assertEqual(verify.status_code, status.HTTP_200_OK)
        self.assertEqual(verify.data['data']['app_entry'], 'staff')
        self.assertEqual(verify.data['data']['app_entry_source'], 'inferred')

    def test_solo_tailor_returning_login_and_infer_app_entry(self):
        first_verify = self._create_solo_tailor(self.TAILOR_PHONE)
        self.assertEqual(first_verify.data['data']['app_entry'], 'tailor')

        login = self._send_otp(self.TAILOR_PHONE)
        self.assertEqual(login.data['data']['account_status'], 'existing')

        verify = self._verify(self.TAILOR_PHONE, name='Solo Tailor')
        self.assertEqual(verify.status_code, status.HTTP_200_OK)
        self.assertEqual(verify.data['data']['app_entry'], 'tailor')
        self.assertEqual(verify.data['data']['app_entry_source'], 'inferred')

    def test_v1_phone_login_has_no_account_status(self):
        response = self.client.post(self.v1_login_url, {'phone': self.V1_PHONE})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('account_status', response.data.get('data', {}))
