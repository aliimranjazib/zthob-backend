"""Tailor config: tailor_plus and shop_plans."""

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.tailors.models import ShopTailorPlusSubscription, TailorProfile
from apps.tailors.services.plans.owner_plans_config import (
    FREE_OWNER_PLAN_FEATURES,
    PLUS_OWNER_PLAN_FEATURES,
)
from apps.tailors.services.plans.pricing import (
    PLUS_PRICE_AMOUNT,
    PLUS_PRICE_FOOTNOTE,
    PLUS_PRICE_LABEL,
    PLUS_VAT_NOTE,
)
from apps.tailors.services.shop_plans_config import (
    FREE_PLAN_FEATURES,
    OWNER_ONLY_FEATURE_KEYS,
    PLUS_PLAN_FEATURES,
)
from zthob.translations import TRANSLATIONS_AR
from zthob.translations_ur import TRANSLATIONS_UR

User = get_user_model()

SHOP_PLUS_REQUIRED_KEYS = {
    'walk_in_orders',
    'crm',
    'order_stages',
    'fabric_inventory',
    'shop_only_products',
    'shop_only_measurements',
    'custom_measurement_fields',
    'dashboard',
    'customer_reports',
    'whatsapp_messages',
    'app_theme',
    'lower_commission',
    'priority_support',
    'payment_gateway_addon',
    'mgask_delivery_addon',
}

OWNER_PLUS_REQUIRED_KEYS = {
    'unlimited_shops',
    'unlimited_staff',
    'branch_comparison',
    'owner_dashboard',
    'dashboard',
    'daily_reports',
    'account_statements',
    'smart_analytics',
    'onboarding',
    'fabric_inventory',
    'app_theme',
    'tailor_plus_all_branches',
}


@override_settings(SECURE_SSL_REDIRECT=False)
class TailorConfigShopPlansTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(
            username='config_plans_owner',
            password='pass',
            role='TAILOR',
        )
        self.shop = self.owner.tailor_profile
        self.shop.shop_name = 'Config Plans Shop'
        self.shop.shop_status = True
        self.shop.save(update_fields=['shop_name', 'shop_status'])
        self.client.force_authenticate(user=self.owner)

    def test_anonymous_config_includes_free_tailor_plus_and_shop_plans(self):
        anonymous = APIClient()
        response = anonymous.get(
            '/api/tailors/config/',
            HTTP_ACCEPT_LANGUAGE='en',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data['data']
        self.assertFalse(data['tailor_plus']['is_active'])
        self.assertEqual(data['tailor_plus']['tier'], 'free')
        self.assertFalse(data['tailor_plus']['entitlements']['walk_in_orders'])
        self.assertTrue(data['tailor_plus']['entitlements']['app_orders'])
        self.assertFalse(data['owner_plus']['entitlements']['owner_dashboard'])
        self.assertEqual(data['shop_plans']['current_tier'], 'free')
        self.assertEqual(len(data['shop_plans']['plans']), 2)
        free_plan = data['shop_plans']['plans'][0]
        plus_plan = data['shop_plans']['plans'][1]
        self.assertEqual(free_plan['tier'], 'free')
        self.assertEqual(plus_plan['tier'], 'plus')
        self.assertEqual(plus_plan['badge_key'], 'recommended')
        self.assertEqual(len(free_plan['features']), len(FREE_PLAN_FEATURES))
        self.assertEqual(len(plus_plan['features']), len(PLUS_PLAN_FEATURES))
        self.assertEqual(free_plan['features'][0]['key'], 'store_setup')
        self.assertEqual(plus_plan['features'][0]['key'], 'walk_in_orders')
        self.assertEqual(
            next(
                feature['text'] for feature in free_plan['features']
                if feature['key'] == 'delivery'
            ),
            'Delivery and measurements managed by the tailor',
        )
        self.assertEqual(
            next(
                feature['text'] for feature in plus_plan['features']
                if feature['key'] == 'mgask_delivery_addon'
            ),
            'Delivery and measurement-taking by Mgask (as agreed)',
        )
        free_keys = {f['key'] for f in free_plan['features']}
        plus_keys = {f['key'] for f in plus_plan['features']}
        self.assertNotIn('app_theme', free_keys)
        self.assertNotIn('mgask_delivery_addon', free_keys)
        self.assertTrue(SHOP_PLUS_REQUIRED_KEYS.issubset(plus_keys))
        self.assertTrue(free_keys.isdisjoint(OWNER_ONLY_FEATURE_KEYS))
        self.assertTrue(plus_keys.isdisjoint(OWNER_ONLY_FEATURE_KEYS))
        self.assertIn('owner_plans', data)
        self.assertIn('owner_plus', data)
        self.assertEqual(len(data['owner_plans']['plans']), 2)

        owner_free = data['owner_plans']['plans'][0]
        owner_plus = data['owner_plans']['plans'][1]
        self.assertEqual(len(owner_free['features']), len(FREE_OWNER_PLAN_FEATURES))
        self.assertEqual(len(owner_plus['features']), len(PLUS_OWNER_PLAN_FEATURES))
        owner_free_keys = {f['key'] for f in owner_free['features']}
        owner_plus_keys = {f['key'] for f in owner_plus['features']}
        self.assertIn('max_shops', owner_free_keys)
        self.assertIn('max_staff', owner_free_keys)
        self.assertIn('owner_fabrics', owner_free_keys)
        self.assertIn('dashboard', owner_free_keys)
        self.assertTrue(OWNER_PLUS_REQUIRED_KEYS.issubset(owner_plus_keys))
        self.assertIn('10', next(
            feature['text'] for feature in owner_plus['features']
            if feature['key'] == 'unlimited_shops'
        ))
        self.assertIn('40', next(
            feature['text'] for feature in owner_plus['features']
            if feature['key'] == 'unlimited_staff'
        ))
        self.assertIn('4', next(
            feature['text'] for feature in owner_free['features']
            if feature['key'] == 'max_staff'
        ))
        self.assertEqual(plus_plan['price']['amount'], PLUS_PRICE_AMOUNT)
        self.assertEqual(plus_plan['price']['label'], PLUS_PRICE_LABEL)
        self.assertEqual(plus_plan['price']['vat_note'], PLUS_VAT_NOTE)
        self.assertEqual(plus_plan['price']['footnote'], PLUS_PRICE_FOOTNOTE)
        self.assertEqual(owner_plus['price']['amount'], PLUS_PRICE_AMOUNT)
        self.assertEqual(owner_plus['price']['label'], PLUS_PRICE_LABEL)
        self.assertEqual(owner_plus['price']['vat_note'], PLUS_VAT_NOTE)
        self.assertEqual(data['tailor_plus']['price']['amount'], PLUS_PRICE_AMOUNT)
        self.assertEqual(data['owner_plus']['price']['vat_note'], PLUS_VAT_NOTE)
        self.assertEqual(free_plan['price']['amount'], 0)
        self.assertEqual(owner_free['price']['label'], 'Free')

    def test_authenticated_free_shop_config(self):
        response = self.client.get('/api/tailors/config/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data['data']
        self.assertFalse(data['tailor_plus']['is_active'])
        self.assertEqual(data['shop_plans']['current_tier'], 'free')
        self.assertIsNone(data['tailor_plus']['limits']['owner_catalog_fabrics_per_shop'])

    def test_authenticated_plus_shop_config(self):
        ShopTailorPlusSubscription.objects.create(
            shop=self.shop,
            status=ShopTailorPlusSubscription.STATUS_ACTIVE,
        )
        response = self.client.get('/api/tailors/config/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data['data']
        self.assertTrue(data['tailor_plus']['is_active'])
        self.assertEqual(data['tailor_plus']['tier'], 'plus')
        self.assertEqual(data['shop_plans']['current_tier'], 'plus')

    def test_shop_plans_title_translated(self):
        response = self.client.get(
            '/api/tailors/config/',
            HTTP_ACCEPT_LANGUAGE='ar',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data['data']['shop_plans']['title'],
            'خطط المتجر',
        )
        shop_plus = response.data['data']['shop_plans']['plans'][1]
        owner_plus = response.data['data']['owner_plans']['plans'][1]
        self.assertEqual(shop_plus['features'][0]['text'], 'أضف طلبات المتجر وعملاء الزيارة')
        shop_free = response.data['data']['shop_plans']['plans'][0]
        self.assertEqual(
            next(
                feature['text'] for feature in shop_free['features']
                if feature['key'] == 'delivery'
            ),
            'التوصيل والمقاسات يديرها الخياط',
        )
        self.assertEqual(owner_plus['name'], 'مالك بلس')
        self.assertEqual(shop_plus['price']['label'], '3,200 ريال / سنوياً')
        self.assertEqual(
            shop_plus['price']['vat_note'],
            'غير شامل ضريبة القيمة المضافة – يعني حوالي 267 ريال شهرياً',
        )
        self.assertEqual(owner_plus['price']['label'], '3,200 ريال / سنوياً')
        self.assertEqual(
            next(
                feature['text'] for feature in owner_plus['features']
                if feature['key'] == 'owner_dashboard'
            ),
            'لوحة مالك مخصصة',
        )

    def test_shop_and_owner_plans_translated_to_urdu(self):
        response = self.client.get(
            '/api/tailors/config/',
            HTTP_ACCEPT_LANGUAGE='ur',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data['data']['shop_plans']['title'],
            'دکان کے پلان',
        )
        shop_plus = response.data['data']['shop_plans']['plans'][1]
        owner_plus = response.data['data']['owner_plans']['plans'][1]
        self.assertEqual(shop_plus['name'], 'خیاط پلس')
        self.assertEqual(owner_plus['name'], 'مالک پلس')
        self.assertEqual(
            shop_plus['features'][0]['text'],
            'دکان کے آرڈرز اور واک اِن گاہک شامل کریں',
        )
        self.assertEqual(shop_plus['price']['label'], '3,200 ریال / سالانہ')
        self.assertEqual(owner_plus['price']['label'], '3,200 ریال / سالانہ')

    def test_every_plan_feature_string_is_localized(self):
        templates = [
            text
            for features in (
                FREE_PLAN_FEATURES,
                PLUS_PLAN_FEATURES,
                FREE_OWNER_PLAN_FEATURES,
                PLUS_OWNER_PLAN_FEATURES,
            )
            for _key, text in features
        ]
        templates.extend(
            [
                PLUS_PRICE_LABEL,
                PLUS_VAT_NOTE,
                PLUS_PRICE_FOOTNOTE,
                'Run your shop with us',
                'Free',
            ]
        )
        missing_ar = [text for text in templates if text not in TRANSLATIONS_AR]
        missing_ur = [text for text in templates if text not in TRANSLATIONS_UR]
        self.assertEqual(missing_ar, [], msg=f'Missing Arabic keys: {missing_ar}')
        self.assertEqual(missing_ur, [], msg=f'Missing Urdu keys: {missing_ur}')
