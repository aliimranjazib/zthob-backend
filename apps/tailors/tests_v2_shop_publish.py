"""Tests for V2 owner shop publish readiness and publish."""

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.core.services import PhoneVerificationService
from apps.tailors.models import ServiceArea, ShopStaffAssignment, TailorProfile

TEST_REST_FRAMEWORK = {
    **settings.REST_FRAMEWORK,
    'DEFAULT_THROTTLE_CLASSES': [],
}


@override_settings(REST_FRAMEWORK=TEST_REST_FRAMEWORK)
class V2ShopPublishAPITestCase(TestCase):
    def setUp(self):
        from apps.accounts import views as account_views

        self._saved_throttles = (
            account_views.PhoneLoginView.throttle_classes,
            account_views.PhoneVerifyView.throttle_classes,
        )
        account_views.PhoneLoginView.throttle_classes = []
        account_views.PhoneVerifyView.throttle_classes = []

        self.client = APIClient()
        self.service_area = ServiceArea.objects.create(
            name='Publish Area',
            city='Riyadh',
            is_active=True,
        )
        self.test_otp = PhoneVerificationService.TEST_OTP
        self.owner_phone = '0500000003'
        self._tiny_png = SimpleUploadedFile(
            'shop.png',
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
            b'\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01'
            b'\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82',
            content_type='image/png',
        )

    def tearDown(self):
        from apps.accounts import views as account_views

        (
            account_views.PhoneLoginView.throttle_classes,
            account_views.PhoneVerifyView.throttle_classes,
        ) = self._saved_throttles

    def _url(self, name, **kwargs):
        if ':' in name and not name.startswith('v2:'):
            name = f'v2:{name}'
        return reverse(name, kwargs=kwargs)

    def _login_owner(self):
        self.client.post(self._url('accounts_v2:v2-phone-login'), {'phone': self.owner_phone})
        response = self.client.post(self._url('accounts_v2:v2-phone-verify'), {
            'phone': self.owner_phone,
            'otp_code': self.test_otp,
            'name': 'Publish Owner',
            'role': 'TAILOR',
            'app_entry': 'owner',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        token = response.data['data']['tokens']['access_token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        self.client.post(
            self._url('tailors_v2:v2-business'),
            {'name': 'Publish Business', 'contact_phone': self.owner_phone},
            format='json',
        )
        return token

    def _create_shop(self, name='Publish Shop'):
        response = self.client.post(self._url('tailors_v2:v2-shops'), {
            'name': name,
            'contact_number': self.owner_phone,
            'address': 'Riyadh',
            'service_area_id': self.service_area.id,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        return response.data['data']

    def _attach_shop_image(self, shop_id: int):
        profile = TailorProfile.objects.get(id=shop_id)
        profile.shop_image = self._tiny_png
        profile.save(update_fields=['shop_image'])

    def _add_manager(self, shop_id: int, phone='0500000004'):
        response = self.client.post(
            self._url('tailors_v2:v2-staff'),
            {
                'name': 'Shop Manager',
                'phone': phone,
                'roles': ['manager'],
                'shop_id': shop_id,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        return response.data['data']

    def test_readiness_draft_shop_missing_staff_and_image(self):
        self._login_owner()
        shop = self._create_shop()
        readiness_url = self._url('tailors_v2:v2-shop-publish-readiness', shop_id=shop['id'])
        response = self.client.get(readiness_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data['data']
        self.assertFalse(data['ready'])
        self.assertEqual(data['review_status'], 'draft')
        keys = {item['key']: item['ok'] for item in data['items']}
        self.assertFalse(keys['operational_staff'])
        self.assertFalse(keys['shop_image'])

    def test_publish_blocked_without_staff(self):
        self._login_owner()
        shop = self._create_shop()
        self._attach_shop_image(shop['id'])
        publish_url = self._url('tailors_v2:v2-shop-publish', shop_id=shop['id'])
        response = self.client.post(publish_url)
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        profile = TailorProfile.objects.get(id=shop['id'])
        self.assertEqual(profile.review.review_status, 'draft')

    def test_publish_succeeds_with_manager_and_profile(self):
        self._login_owner()
        shop = self._create_shop()
        self._attach_shop_image(shop['id'])
        self._add_manager(shop['id'])
        publish_url = self._url('tailors_v2:v2-shop-publish', shop_id=shop['id'])
        response = self.client.post(publish_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['data']['review_status'], 'pending')
        self.assertIsNotNone(response.data['data']['submitted_at'])
        profile = TailorProfile.objects.get(id=shop['id'])
        self.assertEqual(profile.review.review_status, 'pending')

    def test_publish_again_while_pending_returns_400(self):
        self._login_owner()
        shop = self._create_shop()
        self._attach_shop_image(shop['id'])
        self._add_manager(shop['id'])
        publish_url = self._url('tailors_v2:v2-shop-publish', shop_id=shop['id'])
        first = self.client.post(publish_url)
        self.assertEqual(first.status_code, status.HTTP_200_OK)
        second = self.client.post(publish_url)
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)

    def test_stitcher_only_staff_does_not_satisfy_publish(self):
        self._login_owner()
        shop = self._create_shop()
        self._attach_shop_image(shop['id'])
        stitcher = self.client.post(
            self._url('tailors_v2:v2-staff'),
            {
                'name': 'Stitcher Only',
                'phone': '0500000005',
                'roles': ['stitcher'],
                'permissions': ['can_stitch_orders'],
                'shop_id': shop['id'],
            },
            format='json',
        )
        self.assertEqual(stitcher.status_code, status.HTTP_201_CREATED)
        publish_url = self._url('tailors_v2:v2-shop-publish', shop_id=shop['id'])
        response = self.client.post(publish_url)
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    def test_tailor_session_cannot_publish(self):
        owner_token = self._login_owner()
        shop = self._create_shop()
        tailor_phone = '0500000006'
        self.client.credentials()
        self.client.post(self._url('accounts_v2:v2-phone-login'), {'phone': tailor_phone})
        verify = self.client.post(self._url('accounts_v2:v2-phone-verify'), {
            'phone': tailor_phone,
            'otp_code': self.test_otp,
            'name': 'Solo Tailor',
            'role': 'TAILOR',
            'app_entry': 'tailor',
        })
        self.assertIn(verify.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])
        tailor_token = verify.data['data']['tokens']['access_token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {tailor_token}')
        publish_url = self._url('tailors_v2:v2-shop-publish', shop_id=shop['id'])
        response = self.client.post(publish_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {owner_token}')

    def test_orders_permission_without_manager_role_allows_publish(self):
        self._login_owner()
        shop = self._create_shop('Orders Perm Shop')
        self._attach_shop_image(shop['id'])
        staff = self.client.post(
            self._url('tailors_v2:v2-staff'),
            {
                'name': 'Order Lead',
                'phone': '0500000007',
                'roles': ['receptionist'],
                'permissions': ['can_manage_orders'],
                'shop_id': shop['id'],
            },
            format='json',
        )
        self.assertEqual(staff.status_code, status.HTTP_201_CREATED, staff.data)
        assignment = ShopStaffAssignment.objects.get(staff_member_id=staff.data['data']['id'])
        self.assertTrue(assignment.can_manage_orders)
        publish_url = self._url('tailors_v2:v2-shop-publish', shop_id=shop['id'])
        response = self.client.post(publish_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
