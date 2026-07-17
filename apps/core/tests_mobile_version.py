from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.core.mobile_version import (
    compare_versions,
    evaluate_mobile_version,
    get_version_policy,
    mobile_version_cache_key,
)
from apps.core.models import MobileAppVersionPolicy


class MobileVersionUtilsTests(TestCase):
    def test_compare_versions(self):
        self.assertEqual(compare_versions('1.0.27', '1.0.26'), 1)
        self.assertEqual(compare_versions('2.3.1', '2.4.0'), -1)
        self.assertEqual(compare_versions('2.4.0', '2.4.0'), 0)

    def test_evaluate_force_update(self):
        MobileAppVersionPolicy.objects.filter(app='customer', platform='ios').update(
            latest_version='2.5.0',
            soft_update_enabled=False,
            force_update_enabled=True,
        )
        cache.clear()

        result = evaluate_mobile_version('customer', 'ios', '2.3.1')
        self.assertFalse(result['soft_update'])
        self.assertTrue(result['force_update'])

    def test_evaluate_soft_update(self):
        MobileAppVersionPolicy.objects.filter(app='tailor', platform='android').update(
            latest_version='2.0.0',
            soft_update_enabled=True,
            force_update_enabled=False,
        )
        cache.clear()

        result = evaluate_mobile_version('tailor', 'android', '1.5.0')
        self.assertTrue(result['soft_update'])
        self.assertFalse(result['force_update'])

    def test_force_update_wins_when_both_enabled(self):
        MobileAppVersionPolicy.objects.filter(app='tailor', platform='ios').update(
            latest_version='2.0.0',
            soft_update_enabled=True,
            force_update_enabled=True,
        )
        cache.clear()

        result = evaluate_mobile_version('tailor', 'ios', '1.5.0')
        self.assertFalse(result['soft_update'])
        self.assertTrue(result['force_update'])

    def test_evaluate_no_update_when_up_to_date(self):
        MobileAppVersionPolicy.objects.filter(app='rider', platform='ios').update(
            latest_version='1.0.27',
            soft_update_enabled=True,
            force_update_enabled=True,
        )
        cache.clear()

        result = evaluate_mobile_version('rider', 'ios', '1.0.27')
        self.assertFalse(result['soft_update'])
        self.assertFalse(result['force_update'])

    def test_no_update_when_both_flags_disabled(self):
        MobileAppVersionPolicy.objects.filter(app='rider', platform='android').update(
            latest_version='2.0.0',
            soft_update_enabled=False,
            force_update_enabled=False,
        )
        cache.clear()

        result = evaluate_mobile_version('rider', 'android', '1.0.0')
        self.assertFalse(result['soft_update'])
        self.assertFalse(result['force_update'])

    def test_get_version_policy_uses_cache(self):
        MobileAppVersionPolicy.objects.filter(app='customer', platform='android').update(
            latest_version='4.1.0',
        )
        cache.clear()

        policy = get_version_policy('customer', 'android')
        self.assertEqual(policy['latest_version'], '4.1.0')
        self.assertIsNotNone(cache.get(mobile_version_cache_key('customer', 'android')))

    def test_stale_cache_payload_is_ignored(self):
        MobileAppVersionPolicy.objects.filter(app='customer', platform='ios').update(
            latest_version='2.0.0',
            soft_update_enabled=True,
            force_update_enabled=False,
        )
        cache_key = mobile_version_cache_key('customer', 'ios')
        cache.set(
            cache_key,
            {
                'minimum_version': '1.0.0',
                'latest_version': '2.0.0',
                'force_update_enabled': False,
            },
            3600,
        )

        policy = get_version_policy('customer', 'ios')
        self.assertTrue(policy['soft_update_enabled'])

        result = evaluate_mobile_version('customer', 'ios', '1.0.0')
        self.assertTrue(result['soft_update'])
        self.assertFalse(result['force_update'])


class MobileVersionViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        cache.clear()

    def test_all_apps_supported(self):
        for app in ['customer', 'tailor', 'rider']:
            for platform in ['ios', 'android']:
                response = self.client.get(
                    '/api/config/mobile-version/',
                    {'app': app, 'platform': platform, 'version': '1.0.0'},
                )
                self.assertEqual(response.status_code, 200, msg=f'{app}/{platform}')
                self.assertTrue(response.data['success'])
                self.assertIn('soft_update', response.data['data'])
                self.assertIn('force_update', response.data['data'])

    def test_invalid_app_returns_400(self):
        response = self.client.get(
            '/api/config/mobile-version/',
            {'app': 'admin', 'platform': 'ios', 'version': '1.0.0'},
        )
        self.assertEqual(response.status_code, 400)

    def test_missing_version_returns_400(self):
        response = self.client.get(
            '/api/config/mobile-version/',
            {'app': 'customer', 'platform': 'ios'},
        )
        self.assertEqual(response.status_code, 400)

    def test_force_update_response_for_rider(self):
        MobileAppVersionPolicy.objects.filter(app='rider', platform='android').update(
            latest_version='2.0.0',
            soft_update_enabled=False,
            force_update_enabled=True,
        )
        cache.clear()

        response = self.client.get(
            '/api/config/mobile-version/',
            {'app': 'rider', 'platform': 'android', 'version': '1.9.0'},
        )
        self.assertEqual(response.status_code, 200)
        data = response.data['data']
        self.assertTrue(data['force_update'])
        self.assertFalse(data['soft_update'])

    @override_settings(CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    })
    def test_v1_route_supported(self):
        response = self.client.get(
            '/api/v1/config/mobile-version/',
            {'app': 'customer', 'platform': 'ios', 'version': '1.0.0'},
        )
        self.assertEqual(response.status_code, 200)
