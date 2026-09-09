"""
V2 fabric catalog + analytics tests.

Run:
  uv run python manage.py test apps.fabrics.tests.test_v2_fabrics -v 2
"""

from decimal import Decimal
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.core.services import PhoneVerificationService
from apps.customers.models import Address, CustomerProfile
from apps.tailors.models import FabricCategory, FabricImage, ServiceArea, ShopFabric


User = get_user_model()

TEST_REST_FRAMEWORK = {
    **settings.REST_FRAMEWORK,
    'DEFAULT_THROTTLE_CLASSES': [],
}


def _make_test_image(name='fabric.png'):
    return SimpleUploadedFile(
        name,
        (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
            b'\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01'
            b'\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        ),
        content_type='image/png',
    )


@override_settings(
    REST_FRAMEWORK=TEST_REST_FRAMEWORK,
    SECURE_SSL_REDIRECT=False,
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    },
)
class V2FabricCatalogTests(TestCase):
    OWNER_PHONE = '0500000008'
    CUSTOMER_PHONE = '0500000009'
    TEST_OTP = PhoneVerificationService.TEST_OTP

    def setUp(self):
        from apps.accounts import views as account_views

        self._saved_throttles = (
            account_views.PhoneLoginView.throttle_classes,
            account_views.PhoneVerifyView.throttle_classes,
        )
        account_views.PhoneLoginView.throttle_classes = []
        account_views.PhoneVerifyView.throttle_classes = []

        patch(
            'apps.notifications.tasks.send_order_status_notification_task.delay'
        ).start()
        patch(
            'apps.notifications.services.NotificationService.send_new_order_broadcast'
        ).start()
        patch(
            'apps.notifications.services.NotificationService.send_notification'
        ).start()
        patch('apps.customers.services.welcome_sms.queue_customer_welcome_sms').start()
        self.addCleanup(patch.stopall)

        self.client = APIClient()
        self.service_area = ServiceArea.objects.create(
            name='Fabric V2 Area',
            city='Riyadh',
            is_active=True,
        )
        self.fabric_category = FabricCategory.objects.create(name='V2 Fabric Cat', is_active=True)

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

    def _v2_login(self, phone, *, app_entry='owner', name='V2 Fabric Owner'):
        self.client.post(self._url('accounts_v2:v2-phone-login'), {'phone': phone})
        return self.client.post(
            self._url('accounts_v2:v2-phone-verify'),
            {
                'phone': phone,
                'otp_code': self.TEST_OTP,
                'name': name,
                'role': 'TAILOR',
                'app_entry': app_entry,
            },
        )

    def _auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def _setup_owner_shop(self):
        verify = self._v2_login(self.OWNER_PHONE)
        self.assertIn(verify.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])
        token = verify.data['data']['tokens']['access_token']
        self._auth(token)

        self.client.post(
            self._url('tailors_v2:v2-business'),
            {'name': 'Fabric Business', 'contact_phone': self.OWNER_PHONE},
            format='json',
        )
        shop_resp = self.client.post(
            self._url('tailors_v2:v2-shops'),
            {
                'name': 'Fabric Shop',
                'address': 'Riyadh',
                'service_area_id': self.service_area.id,
            },
            format='json',
        )
        self.assertEqual(shop_resp.status_code, status.HTTP_201_CREATED, shop_resp.data)
        shop_id = shop_resp.data['data']['id']

        switch = self.client.post(
            self._url('accounts_v2:v2-switch-shop'),
            {'shop_id': shop_id, 'app_entry': 'owner'},
            format='json',
        )
        self.assertEqual(switch.status_code, status.HTTP_200_OK)
        work_token = switch.data['data']['tokens']['access_token']
        return shop_id, token, work_token

    def test_v2_fabric_product_assign_and_order_sync(self):
        shop_id, owner_token, _work_token = self._setup_owner_shop()
        self._auth(owner_token)

        product_resp = self.client.post(
            self._url('fabrics_v2:v2-fabric-products'),
            {
                'name': 'Premium Cotton',
                'description': 'Soft cotton',
                'price': '180.00',
                'stitching_price': '50.00',
                'category_id': self.fabric_category.id,
                'seasons': 'all_season',
            },
            format='json',
        )
        self.assertEqual(product_resp.status_code, status.HTTP_201_CREATED, product_resp.data)
        product_id = product_resp.data['data']['id']

        assign_resp = self.client.post(
            self._url('fabrics_v2:v2-fabric-product-assign', product_id=product_id),
            {'shop_id': shop_id, 'stock': 10, 'is_visible': True},
            format='json',
        )
        self.assertEqual(assign_resp.status_code, status.HTTP_200_OK, assign_resp.data)
        legacy_fabric_id = assign_resp.data['data']['legacy_fabric_id']
        self.assertIsNotNone(legacy_fabric_id)

        shop_fabrics = self.client.get(self._url('fabrics_v2:v2-shop-fabrics', shop_id=shop_id))
        self.assertEqual(shop_fabrics.status_code, status.HTTP_200_OK)
        self.assertEqual(len(shop_fabrics.data['data']), 1)
        shop_fabric_id = shop_fabrics.data['data'][0]['id']

        stock_resp = self.client.post(
            self._url(
                'fabrics_v2:v2-shop-fabric-stock-movements',
                shop_id=shop_id,
                shop_fabric_id=shop_fabric_id,
            ),
            {'movement_type': 'adjustment_add', 'quantity': 5, 'reason': 'restock'},
            format='json',
        )
        self.assertEqual(stock_resp.status_code, status.HTTP_200_OK, stock_resp.data)
        self.assertEqual(stock_resp.data['data']['stock'], 15)

        order_id = self._create_customer_order(shop_id=shop_id, fabric_id=legacy_fabric_id)
        shop_fabric = ShopFabric.objects.get(id=shop_fabric_id)
        self.assertEqual(shop_fabric.stock, 14)
        self.assertEqual(shop_fabric.stock_movements.filter(movement_type='sale').count(), 1)

        self._auth(owner_token)
        analytics = self.client.get(self._url('fabrics_v2:v2-fabric-analytics'))
        self.assertEqual(analytics.status_code, status.HTTP_200_OK, analytics.data)
        self.assertEqual(analytics.data['data']['summary']['total_units_sold'], 1)
        self.assertEqual(len(analytics.data['data']['by_product']), 1)
        self.assertEqual(analytics.data['data']['by_product'][0]['units_sold'], 1)

        self.assertIsNotNone(order_id)

    def test_v2_multipart_product_create_with_images(self):
        shop_id, owner_token, _work_token = self._setup_owner_shop()
        self._auth(owner_token)

        image = _make_test_image()
        product_resp = self.client.post(
            self._url('fabrics_v2:v2-fabric-products'),
            {
                'name': 'Multipart Cotton',
                'price': '120.00',
                'category_id': str(self.fabric_category.id),
                'images[0][image]': image,
                'images[0][is_primary]': 'true',
                'images[0][order]': '0',
            },
            format='multipart',
        )
        self.assertEqual(product_resp.status_code, status.HTTP_201_CREATED, product_resp.data)
        self.assertEqual(len(product_resp.data['data']['gallery']), 1)

    def test_assign_syncs_product_images_to_legacy_fabric(self):
        shop_id, owner_token, _work_token = self._setup_owner_shop()
        self._auth(owner_token)

        image = _make_test_image()
        product_resp = self.client.post(
            self._url('fabrics_v2:v2-fabric-products'),
            {
                'name': 'Gallery Cotton',
                'price': '150.00',
                'images[0][image]': image,
                'images[0][is_primary]': 'true',
                'images[0][order]': '0',
            },
            format='multipart',
        )
        self.assertEqual(product_resp.status_code, status.HTTP_201_CREATED, product_resp.data)
        product_id = product_resp.data['data']['id']

        assign_resp = self.client.post(
            self._url('fabrics_v2:v2-fabric-product-assign', product_id=product_id),
            {'shop_id': shop_id, 'stock': 3, 'is_visible': True},
            format='json',
        )
        self.assertEqual(assign_resp.status_code, status.HTTP_200_OK, assign_resp.data)
        legacy_fabric_id = assign_resp.data['data']['legacy_fabric_id']
        self.assertEqual(FabricImage.objects.filter(fabric_id=legacy_fabric_id).count(), 1)

    def _create_customer_order(self, *, shop_id, fabric_id):
        from apps.tailors.models import TailorProfile

        customer_client = APIClient()
        customer_client.post(reverse('accounts:phone-login'), {'phone': self.CUSTOMER_PHONE})
        customer_verify = customer_client.post(
            reverse('accounts:phone-verify'),
            {
                'phone': self.CUSTOMER_PHONE,
                'otp_code': self.TEST_OTP,
                'name': 'Fabric Customer',
                'role': 'USER',
            },
        )
        self.assertIn(
            customer_verify.status_code,
            [status.HTTP_200_OK, status.HTTP_201_CREATED],
        )
        customer = User.objects.get(phone=self.CUSTOMER_PHONE)
        CustomerProfile.objects.get_or_create(user=customer)
        address = Address.objects.create(
            user=customer,
            street='Fabric Customer Street',
            city='Riyadh',
            country='Saudi Arabia',
            latitude=Decimal('24.713600'),
            longitude=Decimal('46.675300'),
        )
        customer_client.force_authenticate(user=customer)

        shop = TailorProfile.objects.get(id=shop_id)
        order_resp = customer_client.post(
            reverse('orders:order-create'),
            {
                'tailor': shop.shop_owner_user_id,
                'shop': shop_id,
                'order_type': 'fabric_with_stitching',
                'service_mode': 'home_delivery',
                'payment_method': 'cod',
                'delivery_address': address.id,
                'items': [
                    {
                        'fabric': fabric_id,
                        'quantity': 1,
                        'measurements': {},
                        'custom_instructions': 'V2 fabric catalog order',
                    }
                ],
            },
            format='json',
        )
        self.assertEqual(order_resp.status_code, status.HTTP_201_CREATED, order_resp.data)
        return order_resp.data['data']['id']

    def test_v2_fabric_list_bounded_queries(self):
        shop_id, owner_token, _work_token = self._setup_owner_shop()
        self._auth(owner_token)

        for idx in range(3):
            product_resp = self.client.post(
                self._url('fabrics_v2:v2-fabric-products'),
                {
                    'name': f'Fabric {idx}',
                    'price': '100.00',
                    'category_id': self.fabric_category.id,
                },
                format='json',
            )
            self.assertEqual(product_resp.status_code, status.HTTP_201_CREATED)
            self.client.post(
                self._url(
                    'fabrics_v2:v2-fabric-product-assign',
                    product_id=product_resp.data['data']['id'],
                ),
                {'shop_id': shop_id, 'stock': idx + 1},
                format='json',
            )

        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        with CaptureQueriesContext(connection) as product_ctx:
            products = self.client.get(self._url('fabrics_v2:v2-fabric-products'))
        with CaptureQueriesContext(connection) as shop_ctx:
            shop_fabrics = self.client.get(
                self._url('fabrics_v2:v2-shop-fabrics', shop_id=shop_id)
            )
        self.assertEqual(products.status_code, status.HTTP_200_OK)
        self.assertEqual(shop_fabrics.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(product_ctx), 8)
        self.assertLessEqual(len(shop_ctx), 12)
