"""Tests for owner shop management APIs."""

from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import CustomUser
from apps.core.services import PhoneVerificationService
from apps.tailors.models import TailorProfile

TEST_REST_FRAMEWORK = {
    **settings.REST_FRAMEWORK,
    'DEFAULT_THROTTLE_CLASSES': [],
}


@override_settings(REST_FRAMEWORK=TEST_REST_FRAMEWORK)
class OwnerShopAPITestCase(TestCase):
    def setUp(self):
        from apps.accounts import views as account_views
        from apps.accounts import views_owner as owner_views

        account_views.PhoneLoginView.throttle_classes = []
        account_views.PhoneVerifyView.throttle_classes = []
        owner_views.OwnerPhoneVerifyView.throttle_classes = []

        self.client = APIClient()
        self.phone_login_url = reverse('accounts:phone-login')
        self.owner_verify_url = reverse('accounts:owner-phone-verify')
        self.shops_url = reverse('owner-shops')
        self.test_phone = '0500000003'
        self.test_otp = PhoneVerificationService.TEST_OTP

    def _login_owner(self):
        self.client.post(self.phone_login_url, {'phone': self.test_phone})
        response = self.client.post(self.owner_verify_url, {
            'phone': self.test_phone,
            'otp_code': self.test_otp,
            'name': 'Owner User',
        })
        token = response.data['data']['tokens']['access_token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        return response

    def test_owner_can_create_and_list_multiple_shops(self):
        login_response = self._login_owner()
        self.assertEqual(login_response.status_code, status.HTTP_201_CREATED)

        create_one = self.client.post(self.shops_url, {
            'shop_name': 'Main Branch',
            'address': 'Riyadh',
        }, format='json')
        self.assertEqual(create_one.status_code, status.HTTP_201_CREATED)

        create_two = self.client.post(self.shops_url, {
            'shop_name': 'Mall Branch',
            'address': 'Jeddah',
            'is_pinned': False,
        }, format='json')
        self.assertEqual(create_two.status_code, status.HTTP_201_CREATED)

        list_response = self.client.get(self.shops_url)
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(list_response.data['data']), 2)

    def test_owner_can_pin_and_unpin_shop(self):
        self._login_owner()
        shop = self.client.post(self.shops_url, {
            'shop_name': 'Pin Shop',
            'address': 'Riyadh',
        }, format='json').data['data']

        pin_url = reverse('owner-shop-pin', kwargs={'shop_id': shop['id']})
        unpin = self.client.patch(pin_url, {'is_pinned': False}, format='json')
        self.assertEqual(unpin.status_code, status.HTTP_200_OK)
        self.assertFalse(unpin.data['data']['is_pinned'])

    def test_other_owner_cannot_access_foreign_shop(self):
        self._login_owner()
        shop = self.client.post(self.shops_url, {
            'shop_name': 'Private Shop',
            'address': 'Riyadh',
        }, format='json').data['data']

        other = CustomUser.objects.create_user(
            username='other_owner_2',
            phone='0500000005',
            role='TAILOR',
        )
        TailorProfile.objects.filter(owner=other, user=other).update(shop_name='Other Shop')

        detail_url = reverse('owner-shop-detail', kwargs={'shop_id': shop['id']})
        self.client.force_authenticate(user=other)
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_legacy_phone_verify_still_returns_compact_tailor_context(self):
        self.client.post(self.phone_login_url, {'phone': '0500000004'})
        response = self.client.post(reverse('accounts:phone-verify'), {
            'phone': '0500000004',
            'otp_code': self.test_otp,
            'name': 'Legacy Tailor',
            'role': 'TAILOR',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            set(response.data['data']['tailor_context'].keys()),
            {'is_owner', 'is_employee', 'shop_id', 'roles', 'permissions'},
        )
