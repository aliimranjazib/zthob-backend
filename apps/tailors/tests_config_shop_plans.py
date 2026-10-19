"""Tailor config: tailor_plus and shop_plans."""

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.tailors.models import ShopTailorPlusSubscription, TailorProfile

User = get_user_model()


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
        response = anonymous.get('/api/tailors/config/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data['data']
        self.assertFalse(data['tailor_plus']['is_active'])
        self.assertEqual(data['tailor_plus']['tier'], 'free')
        self.assertEqual(data['shop_plans']['current_tier'], 'free')
        self.assertEqual(len(data['shop_plans']['plans']), 2)
        free_plan = data['shop_plans']['plans'][0]
        plus_plan = data['shop_plans']['plans'][1]
        self.assertEqual(free_plan['tier'], 'free')
        self.assertEqual(plus_plan['tier'], 'plus')
        self.assertEqual(plus_plan['badge_key'], 'recommended')
        self.assertEqual(len(free_plan['features']), 6)
        self.assertEqual(len(plus_plan['features']), 10)
        self.assertEqual(free_plan['features'][0]['key'], 'shop_created_fabrics')
        self.assertIn('30', free_plan['features'][0]['text'])
        self.assertEqual(free_plan['features'][2]['key'], 'fabric_inventory')
        self.assertEqual(plus_plan['features'][0]['key'], 'fabric_inventory')
        free_keys = {f['key'] for f in free_plan['features']}
        plus_keys = {f['key'] for f in plus_plan['features']}
        self.assertNotIn('app_theme', free_keys)
        self.assertIn('app_theme', plus_keys)
        self.assertIn('owner_plans', data)
        self.assertIn('owner_plus', data)
        self.assertEqual(len(data['owner_plans']['plans']), 2)

    def test_authenticated_free_shop_config(self):
        response = self.client.get('/api/tailors/config/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data['data']
        self.assertFalse(data['tailor_plus']['is_active'])
        self.assertEqual(data['shop_plans']['current_tier'], 'free')
        self.assertEqual(
            data['tailor_plus']['limits']['owner_catalog_fabrics_per_shop'],
            30,
        )

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
