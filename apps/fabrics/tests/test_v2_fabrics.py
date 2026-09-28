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

        catalog_resp = self.client.get(self._url('fabrics_v2:v2-fabric-products'))
        self.assertEqual(catalog_resp.status_code, status.HTTP_200_OK, catalog_resp.data)
        catalog_names = [item['name'] for item in catalog_resp.data['data']]
        self.assertIn('Premium Cotton', catalog_names)

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

    def test_create_product_ignores_shop_fields_until_assign(self):
        shop_id, owner_token, _work_token = self._setup_owner_shop()
        self._auth(owner_token)

        product_resp = self.client.post(
            self._url('fabrics_v2:v2-fabric-products'),
            {
                'name': 'Stocked Cotton',
                'price': '200.00',
                'category_id': self.fabric_category.id,
                'shop_id': shop_id,
                'stock': 25,
                'is_visible': True,
            },
            format='json',
        )
        self.assertEqual(product_resp.status_code, status.HTTP_201_CREATED, product_resp.data)
        self.assertEqual(product_resp.data['data']['assigned_shop_count'], 0)
        self.assertEqual(product_resp.data['data']['stock'], 25)

        shop_fabrics = self.client.get(self._url('fabrics_v2:v2-shop-fabrics', shop_id=shop_id))
        self.assertEqual(shop_fabrics.status_code, status.HTTP_200_OK)
        self.assertEqual(shop_fabrics.data['data'], [])

        product_id = product_resp.data['data']['id']
        assign_resp = self.client.post(
            self._url('fabrics_v2:v2-fabric-product-assign', product_id=product_id),
            {'shop_id': shop_id, 'stock': 25, 'is_visible': True},
            format='json',
        )
        self.assertEqual(assign_resp.status_code, status.HTTP_200_OK, assign_resp.data)

        shop_fabrics = self.client.get(self._url('fabrics_v2:v2-shop-fabrics', shop_id=shop_id))
        self.assertEqual(len(shop_fabrics.data['data']), 1)
        self.assertEqual(shop_fabrics.data['data'][0]['stock'], 25)
        self.assertEqual(shop_fabrics.data['data'][0]['product']['name'], 'Stocked Cotton')

    def test_create_product_with_stock_does_not_auto_assign_single_shop(self):
        shop_id, owner_token, _work_token = self._setup_owner_shop()
        self._auth(owner_token)

        product_resp = self.client.post(
            self._url('fabrics_v2:v2-fabric-products'),
            {
                'name': 'Catalog Only Cotton',
                'price': '210.00',
                'stock': 12,
            },
            format='json',
        )
        self.assertEqual(product_resp.status_code, status.HTTP_201_CREATED, product_resp.data)
        self.assertEqual(product_resp.data['data']['assigned_shop_count'], 0)
        self.assertEqual(product_resp.data['data']['stock'], 12)

        shop_fabrics = self.client.get(self._url('fabrics_v2:v2-shop-fabrics', shop_id=shop_id))
        self.assertEqual(shop_fabrics.status_code, status.HTTP_200_OK)
        self.assertEqual(shop_fabrics.data['data'], [])

    def test_create_fabric_without_stock_returns_null_stock(self):
        shop_id, owner_token, _work_token = self._setup_owner_shop()
        self._auth(owner_token)

        product_resp = self.client.post(
            self._url('fabrics_v2:v2-fabric-products'),
            {
                'name': 'No Stock Cotton',
                'price': '190.00',
                'category_id': self.fabric_category.id,
            },
            format='json',
        )
        self.assertEqual(product_resp.status_code, status.HTTP_201_CREATED, product_resp.data)
        self.assertIsNone(product_resp.data['data']['stock'])
        self.assertEqual(product_resp.data['data']['assigned_shop_count'], 0)

        shop_fabrics = self.client.get(self._url('fabrics_v2:v2-shop-fabrics', shop_id=shop_id))
        self.assertEqual(shop_fabrics.data['data'], [])

    def test_assign_without_stock_uses_catalog_default_stock(self):
        shop_id, owner_token, _work_token = self._setup_owner_shop()
        self._auth(owner_token)

        product_resp = self.client.post(
            self._url('fabrics_v2:v2-fabric-products'),
            {
                'name': 'Default Stock Cotton',
                'price': '205.00',
                'stock': 50,
            },
            format='json',
        )
        self.assertEqual(product_resp.status_code, status.HTTP_201_CREATED, product_resp.data)
        product_id = product_resp.data['data']['id']

        assign_resp = self.client.post(
            self._url('fabrics_v2:v2-fabric-product-assign', product_id=product_id),
            {'shop_id': shop_id, 'is_visible': True},
            format='json',
        )
        self.assertEqual(assign_resp.status_code, status.HTTP_200_OK, assign_resp.data)
        self.assertEqual(assign_resp.data['data']['stock'], 50)

        shop_fabrics = self.client.get(self._url('fabrics_v2:v2-shop-fabrics', shop_id=shop_id))
        self.assertEqual(len(shop_fabrics.data['data']), 1)
        self.assertEqual(shop_fabrics.data['data'][0]['stock'], 50)

    def test_assign_with_explicit_stock_overrides_catalog_default(self):
        shop_id, owner_token, _work_token = self._setup_owner_shop()
        self._auth(owner_token)

        product_resp = self.client.post(
            self._url('fabrics_v2:v2-fabric-products'),
            {
                'name': 'Override Stock Cotton',
                'price': '220.00',
                'stock': 50,
            },
            format='json',
        )
        self.assertEqual(product_resp.status_code, status.HTTP_201_CREATED, product_resp.data)
        product_id = product_resp.data['data']['id']

        assign_resp = self.client.post(
            self._url('fabrics_v2:v2-fabric-product-assign', product_id=product_id),
            {'shop_id': shop_id, 'stock': 8, 'is_visible': True},
            format='json',
        )
        self.assertEqual(assign_resp.status_code, status.HTTP_200_OK, assign_resp.data)
        self.assertEqual(assign_resp.data['data']['stock'], 8)

        shop_fabrics = self.client.get(self._url('fabrics_v2:v2-shop-fabrics', shop_id=shop_id))
        self.assertEqual(shop_fabrics.data['data'][0]['stock'], 8)

    def test_create_product_with_stock_does_not_use_jwt_shop(self):
        shop_id, _owner_token, work_token = self._setup_owner_shop()
        self._auth(work_token)

        product_resp = self.client.post(
            self._url('fabrics_v2:v2-fabric-products'),
            {
                'name': 'JWT Shop Cotton',
                'price': '215.00',
                'stock': 18,
            },
            format='json',
        )
        self.assertEqual(product_resp.status_code, status.HTTP_201_CREATED, product_resp.data)
        self.assertEqual(product_resp.data['data']['assigned_shop_count'], 0)

        shop_fabrics = self.client.get(self._url('fabrics_v2:v2-shop-fabrics', shop_id=shop_id))
        self.assertEqual(shop_fabrics.status_code, status.HTTP_200_OK)
        self.assertEqual(shop_fabrics.data['data'], [])

    def test_create_product_with_stock_multiple_shops_creates_catalog_only(self):
        shop_id, owner_token, _work_token = self._setup_owner_shop()
        self._auth(owner_token)

        second_shop_resp = self.client.post(
            self._url('tailors_v2:v2-shops'),
            {
                'name': 'Second Fabric Shop',
                'address': 'Jeddah',
                'service_area_id': self.service_area.id,
            },
            format='json',
        )
        self.assertEqual(second_shop_resp.status_code, status.HTTP_201_CREATED, second_shop_resp.data)

        product_resp = self.client.post(
            self._url('fabrics_v2:v2-fabric-products'),
            {
                'name': 'Ambiguous Stock Cotton',
                'price': '225.00',
                'stock': 5,
            },
            format='json',
        )
        self.assertEqual(product_resp.status_code, status.HTTP_201_CREATED, product_resp.data)
        self.assertEqual(product_resp.data['data']['assigned_shop_count'], 0)

        shop_fabrics = self.client.get(self._url('fabrics_v2:v2-shop-fabrics', shop_id=shop_id))
        self.assertEqual(shop_fabrics.data['data'], [])

    def test_patch_product_appends_images(self):
        shop_id, owner_token, _work_token = self._setup_owner_shop()
        self._auth(owner_token)

        product_resp = self.client.post(
            self._url('fabrics_v2:v2-fabric-products'),
            {
                'name': 'Patch Gallery Cotton',
                'price': '130.00',
            },
            format='json',
        )
        self.assertEqual(product_resp.status_code, status.HTTP_201_CREATED, product_resp.data)
        product_id = product_resp.data['data']['id']

        assign_resp = self.client.post(
            self._url('fabrics_v2:v2-fabric-product-assign', product_id=product_id),
            {'shop_id': shop_id, 'stock': 4, 'is_visible': True},
            format='json',
        )
        self.assertEqual(assign_resp.status_code, status.HTTP_200_OK, assign_resp.data)

        patch_resp = self.client.patch(
            self._url('fabrics_v2:v2-fabric-product-detail', product_id=product_id),
            {
                'description': 'Updated description',
                'images[0][image]': _make_test_image('patch.png'),
                'images[0][is_primary]': 'true',
                'images[0][order]': '0',
            },
            format='multipart',
        )
        self.assertEqual(patch_resp.status_code, status.HTTP_200_OK, patch_resp.data)
        self.assertEqual(patch_resp.data['data']['description'], 'Updated description')
        self.assertEqual(len(patch_resp.data['data']['gallery']), 1)

    def test_patch_product_appends_images_syncs_legacy_fabric(self):
        shop_id, owner_token, _work_token = self._setup_owner_shop()
        self._auth(owner_token)

        product_resp = self.client.post(
            self._url('fabrics_v2:v2-fabric-products'),
            {
                'name': 'Legacy Sync Cotton',
                'price': '140.00',
            },
            format='json',
        )
        product_id = product_resp.data['data']['id']

        assign_resp = self.client.post(
            self._url('fabrics_v2:v2-fabric-product-assign', product_id=product_id),
            {'shop_id': shop_id, 'stock': 2, 'is_visible': True},
            format='json',
        )
        self.assertEqual(assign_resp.status_code, status.HTTP_200_OK, assign_resp.data)

        self.client.patch(
            self._url('fabrics_v2:v2-fabric-product-detail', product_id=product_id),
            {
                'images[0][image]': _make_test_image('legacy-sync.png'),
                'images[0][is_primary]': 'true',
                'images[0][order]': '0',
            },
            format='multipart',
        )

        shop_fabrics = self.client.get(self._url('fabrics_v2:v2-shop-fabrics', shop_id=shop_id))
        legacy_fabric_id = shop_fabrics.data['data'][0]['legacy_fabric_id']
        self.assertEqual(FabricImage.objects.filter(fabric_id=legacy_fabric_id).count(), 1)

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

    def test_shop_scoped_create_hidden_from_owner_catalog(self):
        shop_id, owner_token, _work_token = self._setup_owner_shop()
        self._auth(owner_token)

        shop_resp = self.client.post(
            self._url('fabrics_v2:v2-shop-fabrics', shop_id=shop_id),
            {
                'name': 'Shop Only Cotton',
                'price': '150.00',
                'stock': 8,
                'category_id': self.fabric_category.id,
            },
            format='json',
        )
        self.assertEqual(shop_resp.status_code, status.HTTP_201_CREATED, shop_resp.data)
        self.assertFalse(shop_resp.data['data']['product']['show_in_owner_catalog'])

        catalog_resp = self.client.get(self._url('fabrics_v2:v2-fabric-products'))
        self.assertEqual(catalog_resp.status_code, status.HTTP_200_OK, catalog_resp.data)
        catalog_names = [item['name'] for item in catalog_resp.data['data']]
        self.assertNotIn('Shop Only Cotton', catalog_names)

        shop_fabrics = self.client.get(self._url('fabrics_v2:v2-shop-fabrics', shop_id=shop_id))
        self.assertEqual(shop_fabrics.status_code, status.HTTP_200_OK, shop_fabrics.data)
        shop_names = [item['product']['name'] for item in shop_fabrics.data['data']]
        self.assertIn('Shop Only Cotton', shop_names)

    def test_v1_linked_shop_fabric_hidden_from_owner_catalog(self):
        from apps.fabrics.services.legacy_bridge import link_legacy_fabric_to_business_catalog
        from apps.tailors.models import Fabric, TailorProfile

        shop_id, owner_token, _work_token = self._setup_owner_shop()
        shop = TailorProfile.objects.get(id=shop_id)
        fabric = Fabric.objects.create(
            tailor=shop,
            name='V1 Shop Cotton',
            price=Decimal('120.00'),
            stock=3,
            seasons='all_season',
            approval_status='approved',
        )
        shop_fabric = link_legacy_fabric_to_business_catalog(fabric=fabric)
        self.assertIsNotNone(shop_fabric)
        self.assertFalse(shop_fabric.product.show_in_owner_catalog)

        self._auth(owner_token)
        catalog_resp = self.client.get(self._url('fabrics_v2:v2-fabric-products'))
        self.assertEqual(catalog_resp.status_code, status.HTTP_200_OK, catalog_resp.data)
        catalog_names = [item['name'] for item in catalog_resp.data['data']]
        self.assertNotIn('V1 Shop Cotton', catalog_names)

        shop_fabrics = self.client.get(self._url('fabrics_v2:v2-shop-fabrics', shop_id=shop_id))
        self.assertEqual(shop_fabrics.status_code, status.HTTP_200_OK, shop_fabrics.data)
        shop_names = [item['product']['name'] for item in shop_fabrics.data['data']]
        self.assertIn('V1 Shop Cotton', shop_names)
