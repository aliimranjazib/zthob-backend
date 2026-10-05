"""Per-shop rider teams for multi-shop owners."""

from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import CustomUser
from apps.core.services import PhoneVerificationService
from apps.riders.models import RiderProfile, RiderProfileReview, TailorRiderAssociation
from apps.tailors.models import TailorProfile

TEST_REST_FRAMEWORK = {
    **settings.REST_FRAMEWORK,
    'DEFAULT_THROTTLE_CLASSES': [],
}


@override_settings(REST_FRAMEWORK=TEST_REST_FRAMEWORK)
class MultiShopRidersTestCase(TestCase):
    def setUp(self):
        from apps.accounts import views as account_views

        account_views.PhoneLoginView.throttle_classes = []
        account_views.PhoneVerifyView.throttle_classes = []

        self.client = APIClient()
        self.phone_login_url = reverse('accounts:phone-login')
        self.phone_verify_url = reverse('accounts:phone-verify')
        self.owner_switch_url = reverse('accounts:owner-switch-shop')
        self.shops_url = reverse('owner-shops')
        self.my_riders_url = '/api/riders/tailor/my-riders/'
        self.test_otp = PhoneVerificationService.TEST_OTP
        self.owner_phone = '0500000201'

        self.rider = CustomUser.objects.create_user(
            username='multi_shop_rider',
            password='testpass123',
            role='RIDER',
        )
        profile, _ = RiderProfile.objects.get_or_create(user=self.rider)
        profile.full_name = 'Multi Shop Rider'
        profile.save(update_fields=['full_name'])
        review, _ = RiderProfileReview.objects.get_or_create(profile=profile)
        review.review_status = 'approved'
        review.save(update_fields=['review_status'])

    def _login_owner(self):
        self.client.post(self.phone_login_url, {'phone': self.owner_phone})
        response = self.client.post(self.phone_verify_url, {
            'phone': self.owner_phone,
            'otp_code': self.test_otp,
            'name': 'Rider Owner',
            'role': 'TAILOR',
            'app_entry': 'owner',
        })
        token = response.data['data']['tokens']['access_token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        return response

    def _create_shop(self, name):
        response = self.client.post(
            self.shops_url,
            {'shop_name': name, 'address': 'Riyadh'},
            format='json',
        )
        return response.data['data']

    def _switch_shop(self, shop_id):
        response = self.client.post(
            self.owner_switch_url,
            {'shop_id': shop_id},
            format='json',
        )
        token = response.data['data']['tokens']['access_token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_riders_list_scoped_to_active_shop(self):
        self._login_owner()
        owner = CustomUser.objects.get(phone=self.owner_phone)
        shop_a = self._create_shop('Riders Shop A')
        shop_b = self._create_shop('Riders Shop B')

        shop_a_profile = TailorProfile.objects.get(id=shop_a['id'])
        TailorRiderAssociation.objects.create(
            tailor=owner,
            shop=shop_a_profile,
            rider=self.rider,
            is_active=True,
        )

        self._switch_shop(shop_a['id'])
        response_a = self.client.get(self.my_riders_url)
        self.assertEqual(response_a.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response_a.data['data']['riders']), 1)

        self._switch_shop(shop_b['id'])
        response_b = self.client.get(self.my_riders_url)
        self.assertEqual(response_b.status_code, status.HTTP_200_OK)
        self.assertEqual(response_b.data['data']['riders'], [])
