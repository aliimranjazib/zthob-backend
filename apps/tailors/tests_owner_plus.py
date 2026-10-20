"""Owner Plus subscription and bundled Tailor Plus entitlements."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.fabrics.models import FabricProduct
from apps.tailors.models import Business, BusinessOwnerPlusSubscription, TailorProfile, TailorStaffMember
from apps.tailors.services.plans.owner_limits import (
    OwnerPlanLimitError,
    assert_can_add_staff_member,
    assert_can_create_shop,
    validate_report_period_for_owner,
)
from apps.tailors.services.plans.constants import OWNER_PLUS_MAX_SHOPS
from apps.tailors.services.shop_plus import is_shop_plus_active, resolve_shop_plus_source

User = get_user_model()


@override_settings(SECURE_SSL_REDIRECT=False)
class OwnerPlusBundleTest(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username='owner_plus_user',
            password='pass',
            role='TAILOR',
        )
        self.shop = self.owner.tailor_profile
        self.shop.shop_name = 'Bundle Shop'
        self.shop.shop_status = True
        self.business = Business.objects.create(
            owner=self.owner,
            name='Bundle Biz',
            contact_phone='0500000001',
        )
        self.shop.business = self.business
        self.shop.save(update_fields=['shop_name', 'shop_status', 'business'])

    def test_owner_plus_grants_shop_plus_without_shop_subscription(self):
        self.assertFalse(is_shop_plus_active(self.shop))
        BusinessOwnerPlusSubscription.objects.create(
            business=self.business,
            status=BusinessOwnerPlusSubscription.STATUS_ACTIVE,
        )
        self.assertTrue(is_shop_plus_active(self.shop))
        self.assertEqual(resolve_shop_plus_source(self.shop), 'owner_bundle')

    def test_direct_shop_plus_takes_precedence_source(self):
        from apps.tailors.models import ShopTailorPlusSubscription

        BusinessOwnerPlusSubscription.objects.create(
            business=self.business,
            status=BusinessOwnerPlusSubscription.STATUS_ACTIVE,
        )
        ShopTailorPlusSubscription.objects.create(
            shop=self.shop,
            status=ShopTailorPlusSubscription.STATUS_ACTIVE,
        )
        self.assertEqual(resolve_shop_plus_source(self.shop), 'shop')


@override_settings(SECURE_SSL_REDIRECT=False)
class OwnerFreeLimitsTest(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username='free_owner_limits',
            password='pass',
            role='TAILOR',
        )
        self.business = Business.objects.create(
            owner=self.owner,
            name='Limit Biz',
            contact_phone='0500000002',
        )
        TailorProfile.objects.create(
            owner=self.owner,
            shop_name='Branch 0',
            shop_status=True,
            business=self.business,
        )

    def test_free_owner_blocked_from_second_shop(self):
        with self.assertRaises(OwnerPlanLimitError):
            assert_can_create_shop(owner=self.owner, creating_new_named_shop=True)

    def test_free_owner_blocked_from_fifth_staff_member(self):
        for index in range(4):
            user = User.objects.create_user(
                username=f'staff_limit_{index}',
                password='pass',
                role='TAILOR',
            )
            TailorStaffMember.objects.create(owner=self.owner, user=user, is_active=True)
        with self.assertRaises(OwnerPlanLimitError):
            assert_can_add_staff_member(owner=self.owner, is_new_active_member=True)

    def test_free_owner_can_manage_fabrics_without_count_cap(self):
        from apps.tailors.services.plans.owner_limits import (
            assert_can_create_owner_catalog_product,
        )

        for index in range(31):
            FabricProduct.objects.create(
                business=self.business,
                name=f'Fabric {index}',
                price=Decimal('10.00'),
            )
        assert_can_create_owner_catalog_product(
            business=self.business,
            owner=self.owner,
        )

    def test_owner_plus_caps_shops_at_ten(self):
        from apps.accounts.services.v2_auth import count_active_shops
        from apps.tailors.models import BusinessOwnerPlusSubscription

        BusinessOwnerPlusSubscription.objects.create(
            business=self.business,
            status=BusinessOwnerPlusSubscription.STATUS_ACTIVE,
        )
        current = count_active_shops(self.owner.id)
        for index in range(current, OWNER_PLUS_MAX_SHOPS):
            TailorProfile.objects.create(
                owner=self.owner,
                shop_name=f'Plus Branch {index}',
                shop_status=True,
                business=self.business,
            )
        with self.assertRaises(OwnerPlanLimitError) as ctx:
            assert_can_create_shop(owner=self.owner, creating_new_named_shop=True)
        self.assertEqual(ctx.exception.detail['entitlement'], 'max_shops')


@override_settings(SECURE_SSL_REDIRECT=False)
class TailorConfigOwnerPlansTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(
            username='config_owner_plus',
            password='pass',
            role='TAILOR',
        )
        self.shop = self.owner.tailor_profile
        self.shop.shop_name = 'Config Owner Shop'
        self.shop.shop_status = True
        self.shop.save(update_fields=['shop_name', 'shop_status'])
        self.business = Business.objects.create(
            owner=self.owner,
            name='Config Biz',
            contact_phone='0500000003',
        )
        self.client.force_authenticate(user=self.owner)

    def test_config_includes_owner_plans(self):
        response = self.client.get('/api/tailors/config/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data['data']
        self.assertIn('owner_plus', data)
        self.assertIn('owner_plans', data)
        self.assertEqual(data['owner_plans']['current_tier'], 'free')
        self.assertEqual(len(data['owner_plans']['plans']), 2)
        self.assertTrue(data['owner_plus']['applicable'])

    def test_owner_plus_active_in_config(self):
        BusinessOwnerPlusSubscription.objects.create(
            business=self.business,
            status=BusinessOwnerPlusSubscription.STATUS_ACTIVE,
        )
        response = self.client.get('/api/tailors/config/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data['data']
        self.assertEqual(data['owner_plans']['current_tier'], 'plus')
        self.assertTrue(data['owner_plus']['is_active'])
        self.assertTrue(data['tailor_plus']['is_active'])
        self.assertEqual(data['tailor_plus']['plus_source'], 'owner_bundle')
        self.assertEqual(data['owner_plus']['limits']['max_shops'], 10)
        self.assertEqual(data['owner_plus']['limits']['max_staff'], 40)
        self.assertTrue(data['tailor_plus']['entitlements']['walk_in_orders'])
        self.assertTrue(data['owner_plus']['entitlements']['tailor_plus_all_branches'])


@override_settings(SECURE_SSL_REDIRECT=False)
class OwnerAggregateReportsLimitTest(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username='reports_owner_plus',
            password='pass',
            role='TAILOR',
        )

    def test_free_owner_blocks_this_month_aggregate(self):
        with self.assertRaises(OwnerPlanLimitError):
            validate_report_period_for_owner(self.owner, period='this_month')
