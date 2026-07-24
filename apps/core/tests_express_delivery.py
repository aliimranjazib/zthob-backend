from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.core.express_delivery import (
    default_express_delivery_options,
    get_express_delivery_options,
    is_allowed_express_selection,
    normalize_express_option,
)
from apps.core.models import SystemSettings


@override_settings(
    SECURE_SSL_REDIRECT=False,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}},
)
class ExpressDeliveryOptionsTest(TestCase):
    def setUp(self):
        cache.clear()
        self.settings_obj = SystemSettings.get_active_settings()
        self.settings_obj.express_delivery_max_days = 3
        self.settings_obj.express_delivery_options = None
        self.settings_obj.save()
        cache.clear()
        self.client = APIClient()

    def test_defaults_include_six_hours_and_days(self):
        options = default_express_delivery_options(3)
        self.assertEqual(options[0], {'value': 6, 'unit': 'hours', 'label': '6 Hours'})
        self.assertEqual(
            [(o['unit'], o['value']) for o in options[1:]],
            [('days', 1), ('days', 2), ('days', 3)],
        )

    def test_admin_custom_options_used_by_config_api(self):
        self.settings_obj.express_delivery_options = [
            {'value': 6, 'unit': 'hours', 'label': '6 Hours'},
            {'value': 12, 'unit': 'hours', 'label': '12 Hours'},
            {'days': 1, 'display_name': '1 Day'},
        ]
        self.settings_obj.save()
        cache.clear()

        response = self.client.get('/api/tailors/config/')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        options = response.data['data']['express_delivery_options']
        pairs = [(o['unit'], o['value']) for o in options]
        self.assertEqual(pairs, [('hours', 6), ('hours', 12), ('days', 1)])
        six_hours = options[0]
        self.assertEqual(six_hours['hours'], 6)
        self.assertIsNone(six_hours['days'])
        self.assertEqual(six_hours['display_name'], '6 Hours')

    def test_empty_options_fall_back_to_defaults_with_six_hours(self):
        options = get_express_delivery_options(self.settings_obj)
        self.assertEqual(options[0]['unit'], 'hours')
        self.assertEqual(options[0]['value'], 6)
        self.assertTrue(is_allowed_express_selection(6, 'hours', self.settings_obj))
        self.assertTrue(is_allowed_express_selection(2, 'days', self.settings_obj))
        self.assertFalse(is_allowed_express_selection(99, 'days', self.settings_obj))

    def test_normalize_accepts_hours_and_days_shapes(self):
        self.assertEqual(
            normalize_express_option({'hours': 6, 'display_name': 'Six'}),
            {
                'value': 6,
                'unit': 'hours',
                'label': 'Six',
                'hours': 6,
                'days': None,
            },
        )
        self.assertEqual(
            normalize_express_option({'days': 2})['unit'],
            'days',
        )
