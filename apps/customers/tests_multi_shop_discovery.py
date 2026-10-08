"""Customer discovery lists each owner branch as a separate shop."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.customers.models import Address
from apps.orders.models import Order
from apps.tailors.models import Fabric, TailorProfile, TailorProfileReview

User = get_user_model()

RIYADH_LAT = 24.7136
RIYADH_LNG = 46.6753


@override_settings(
    SECURE_SSL_REDIRECT=False,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}},
)
class CustomerMultiShopDiscoveryTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(
            username='multi_owner',
            password='testpass123',
            role='TAILOR',
        )
        self.primary = self.owner.tailor_profile
        self.primary.shop_name = 'Primary Branch'
        self.primary.shop_status = True
        self.primary.save()
        TailorProfileReview.objects.update_or_create(
            profile=self.primary,
            defaults={'review_status': 'approved'},
        )

        self.branch_b = TailorProfile.objects.create(
            owner=self.owner,
            user=None,
            shop_name='Mall Branch',
            shop_status=True,
            address='Mall address, Riyadh',
        )
        TailorProfileReview.objects.create(
            profile=self.branch_b,
            review_status='approved',
        )

        Address.objects.create(
            user=self.owner,
            address='Owner shop address',
            street='Owner Street',
            city='Riyadh',
            country='Saudi Arabia',
            latitude=RIYADH_LAT,
            longitude=RIYADH_LNG,
            address_tag='shop',
            is_default=True,
        )

        self.fabric_b = Fabric.objects.create(
            name='Branch B Cotton',
            tailor=self.branch_b,
            price=Decimal('100.00'),
            is_active=True,
            approval_status='approved',
        )

    def test_home_new_tailors_lists_all_approved_shops(self):
        response = self.client.get(
            f'/api/customers/home/?lat={RIYADH_LAT}&lng={RIYADH_LNG}&radius=50'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = {item['shop_name'] for item in response.data['data']['new_tailors']}
        self.assertIn('Primary Branch', names)
        self.assertIn('Mall Branch', names)

    def test_tailor_list_returns_distinct_shop_ids(self):
        response = self.client.get('/api/customers/tailors/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        shop_ids = {item['id'] for item in response.data['data']['results']}
        self.assertIn(self.primary.id, shop_ids)
        self.assertIn(self.branch_b.id, shop_ids)

    def test_detail_and_fabrics_resolve_by_shop_id(self):
        detail = self.client.get(f'/api/customers/tailors/{self.branch_b.id}/')
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        self.assertEqual(detail.data['data']['shop_name'], 'Mall Branch')
        self.assertEqual(detail.data['data']['tailor_user_id'], self.owner.id)

        fabrics = self.client.get(f'/api/customers/tailors/{self.branch_b.id}/fabrics')
        self.assertEqual(fabrics.status_code, status.HTTP_200_OK)
        fabric_ids = {row['id'] for row in fabrics.data['data']['results']}
        self.assertIn(self.fabric_b.id, fabric_ids)

    def test_legacy_user_id_still_opens_primary_shop(self):
        response = self.client.get(f'/api/customers/tailors/{self.owner.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['id'], self.primary.id)
