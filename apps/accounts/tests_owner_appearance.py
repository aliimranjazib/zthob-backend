"""Owner app appearance / theme preference API tests."""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.appearance import DEFAULT_APPEARANCE, appearance_for_user
from apps.core.services import PhoneVerificationService
from apps.tailors.models import ShopTailorPlusSubscription, TailorProfile

User = get_user_model()

TEST_REST_FRAMEWORK = {
    **settings.REST_FRAMEWORK,
    'DEFAULT_THROTTLE_CLASSES': [],
}


@override_settings(REST_FRAMEWORK=TEST_REST_FRAMEWORK)
class OwnerAppearanceTests(TestCase):
    def setUp(self):
        from apps.accounts import views as account_views

        self._saved_throttles = (
            account_views.PhoneLoginView.throttle_classes,
            account_views.PhoneVerifyView.throttle_classes,
        )
        account_views.PhoneLoginView.throttle_classes = []
        account_views.PhoneVerifyView.throttle_classes = []

        self.client = APIClient()
        self.phone_login_url = reverse('accounts:phone-login')
        self.phone_verify_url = reverse('accounts:phone-verify')
        self.owner_profile_url = reverse('accounts:owner-profile')
        self.test_otp = PhoneVerificationService.TEST_OTP

    def tearDown(self):
        from apps.accounts import views as account_views

        (
            account_views.PhoneLoginView.throttle_classes,
            account_views.PhoneVerifyView.throttle_classes,
        ) = self._saved_throttles

    def _owner_login(self, phone='0522222220', *, name='Theme Owner'):
        login = self.client.post(self.phone_login_url, {'phone': phone})
        verification_id = login.data['data']['verification_id']
        return self.client.post(
            self.phone_verify_url,
            {
                'verification_id': verification_id,
                'otp_code': self.test_otp,
                'name': name,
                'role': 'TAILOR',
                'app_entry': 'owner',
            },
            format='json',
            HTTP_X_APP_ENTRY='owner',
        )

    def test_login_includes_default_appearance(self):
        response = self._owner_login()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user_data = response.data['data']['user']
        self.assertEqual(user_data['appearance'], DEFAULT_APPEARANCE)

    def test_owner_profile_patch_custom_seed(self):
        phone = '0522222221'
        login = self._owner_login(phone=phone)
        user = User.objects.get(phone=phone)
        shop, _ = TailorProfile.objects.get_or_create(
            owner=user,
            defaults={'shop_name': 'Theme Shop'},
        )
        ShopTailorPlusSubscription.objects.get_or_create(
            shop=shop,
            defaults={'status': ShopTailorPlusSubscription.STATUS_ACTIVE},
        )
        token = login.data['data']['tokens']['access_token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        get_response = self.client.get(self.owner_profile_url)
        self.assertEqual(get_response.status_code, status.HTTP_200_OK)
        self.assertEqual(get_response.data['data']['appearance'], DEFAULT_APPEARANCE)

        patch_response = self.client.patch(
            self.owner_profile_url,
            {
                'appearance': {
                    'version': 1,
                    'mode': 'dark',
                    'preset_id': None,
                    'seed_color': '#1E88E5',
                },
            },
            format='json',
        )
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        appearance = patch_response.data['data']['appearance']
        self.assertEqual(appearance['mode'], 'dark')
        self.assertEqual(appearance['seed_color'], '#1E88E5')
        self.assertIsNone(appearance['preset_id'])
        self.assertIsNotNone(patch_response.data['data']['appearance_updated_at'])

        user.refresh_from_db()
        self.assertEqual(appearance_for_user(user)['seed_color'], '#1E88E5')

    def test_second_login_returns_saved_appearance(self):
        phone = '0522222222'
        login = self._owner_login(phone=phone)
        user = User.objects.get(phone=phone)
        shop, _ = TailorProfile.objects.get_or_create(
            owner=user,
            defaults={'shop_name': 'Theme Shop 2'},
        )
        ShopTailorPlusSubscription.objects.get_or_create(
            shop=shop,
            defaults={'status': ShopTailorPlusSubscription.STATUS_ACTIVE},
        )
        token = login.data['data']['tokens']['access_token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        self.client.patch(
            self.owner_profile_url,
            {
                'appearance': {
                    'version': 1,
                    'mode': 'light',
                    'preset_id': 'mgask_default',
                },
            },
            format='json',
        )

        login2 = self._owner_login(phone=phone, name='Theme Owner')
        self.assertEqual(login2.status_code, status.HTTP_200_OK)
        appearance = login2.data['data']['user']['appearance']
        self.assertEqual(appearance['preset_id'], 'mgask_default')
        self.assertEqual(appearance['mode'], 'light')

    def test_invalid_appearance_rejected(self):
        phone = '0522222223'
        login = self._owner_login(phone=phone)
        user = User.objects.get(phone=phone)
        TailorProfile.objects.get_or_create(
            owner=user,
            defaults={'shop_name': 'Theme Shop 3'},
        )
        token = login.data['data']['tokens']['access_token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        response = self.client.patch(
            self.owner_profile_url,
            {
                'appearance': {
                    'version': 1,
                    'mode': 'dark',
                    'preset_id': None,
                    'seed_color': 'not-a-color',
                },
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])

    def test_expired_plus_returns_default_appearance_instantly(self):
        phone = '0522222224'
        login = self._owner_login(phone=phone)
        user = User.objects.get(phone=phone)
        shop, _ = TailorProfile.objects.get_or_create(
            owner=user,
            defaults={'shop_name': 'Theme Shop 4'},
        )
        subscription, _ = ShopTailorPlusSubscription.objects.get_or_create(
            shop=shop,
            defaults={'status': ShopTailorPlusSubscription.STATUS_ACTIVE},
        )
        token = login.data['data']['tokens']['access_token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        self.client.patch(
            self.owner_profile_url,
            {
                'appearance': {
                    'version': 1,
                    'mode': 'dark',
                    'preset_id': None,
                    'seed_color': '#1E88E5',
                },
            },
            format='json',
        )

        subscription.status = ShopTailorPlusSubscription.STATUS_EXPIRED
        subscription.save(update_fields=['status'])

        user.refresh_from_db()
        self.assertEqual(user.appearance['seed_color'], '#1E88E5')
        self.assertEqual(appearance_for_user(user), DEFAULT_APPEARANCE)

        profile = self.client.get(self.owner_profile_url)
        self.assertEqual(profile.status_code, status.HTTP_200_OK)
        self.assertEqual(profile.data['data']['appearance'], DEFAULT_APPEARANCE)

        subscription.status = ShopTailorPlusSubscription.STATUS_ACTIVE
        subscription.save(update_fields=['status'])
        self.assertEqual(appearance_for_user(user)['seed_color'], '#1E88E5')
