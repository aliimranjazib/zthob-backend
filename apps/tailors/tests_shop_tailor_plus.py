"""Shop-scoped Tailor Plus subscription."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.fabrics.models import FabricProduct, ShopFabric
from apps.tailors.models import ShopTailorPlusSubscription, TailorProfile
from apps.tailors.services.shop_plus import (
    assert_can_add_fabric_to_shop,
    is_shop_plus_active,
    TailorPlusLimitError,
)

User = get_user_model()


@override_settings(SECURE_SSL_REDIRECT=False)
class ShopTailorPlusServiceTest(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username='plus_owner',
            password='pass',
            role='TAILOR',
        )
        self.shop = TailorProfile.objects.create(
            owner=self.owner,
            user=self.owner,
            shop_name='Plus Test Shop',
            shop_status=True,
        )

    def _activate_plus(self):
        ShopTailorPlusSubscription.objects.create(
            shop=self.shop,
            status=ShopTailorPlusSubscription.STATUS_ACTIVE,
        )

    def test_inactive_without_subscription(self):
        self.assertFalse(is_shop_plus_active(self.shop))

    def test_active_subscription(self):
        self._activate_plus()
        self.assertTrue(is_shop_plus_active(self.shop))

    def test_free_shop_fabric_limit(self):
        for index in range(30):
            product = FabricProduct.objects.create(
                business_id=self._ensure_business().id,
                name=f'Shop Fabric {index}',
                price=Decimal('10.00'),
                show_in_owner_catalog=False,
            )
            ShopFabric.objects.create(shop=self.shop, product=product, stock=1, is_active=True)

        with self.assertRaises(TailorPlusLimitError):
            assert_can_add_fabric_to_shop(shop=self.shop, owner_catalog=False)

        self._activate_plus()
        assert_can_add_fabric_to_shop(shop=self.shop, owner_catalog=False)

    def _ensure_business(self):
        from apps.tailors.models import Business

        business, _ = Business.objects.get_or_create(
            owner=self.owner,
            defaults={'name': 'Plus Biz', 'contact_phone': '0500000000'},
        )
        self.shop.business = business
        self.shop.save(update_fields=['business'])
        return business


class ShopTailorPlusOwnerReportsTest(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username='reports_owner',
            password='pass',
            role='TAILOR',
        )
        self.shop = TailorProfile.objects.create(
            owner=self.owner,
            user=self.owner,
            shop_name='Reports Shop',
            shop_status=True,
        )

    def test_free_shop_blocks_long_report_period(self):
        from apps.tailors.services.shop_plus import (
            TailorPlusLimitError,
            validate_report_period_for_shop,
        )

        with self.assertRaises(TailorPlusLimitError):
            validate_report_period_for_shop(self.shop, period='this_month')

    def test_plus_shop_allows_long_report_period(self):
        from apps.tailors.services.shop_plus import validate_report_period_for_shop

        ShopTailorPlusSubscription.objects.create(
            shop=self.shop,
            status=ShopTailorPlusSubscription.STATUS_ACTIVE,
        )
        validate_report_period_for_shop(self.shop, period='this_month')
