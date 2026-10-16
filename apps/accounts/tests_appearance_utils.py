from django.test import SimpleTestCase

from apps.accounts.appearance import DEFAULT_APPEARANCE, normalize_appearance


class AppearanceUtilsTests(SimpleTestCase):
    def test_default_when_empty(self):
        self.assertEqual(normalize_appearance({}), DEFAULT_APPEARANCE)

    def test_custom_seed_uppercase(self):
        result = normalize_appearance(
            {
                'version': 1,
                'mode': 'system',
                'preset_id': None,
                'seed_color': '#abc123',
            }
        )
        self.assertEqual(result['seed_color'], '#ABC123')
        self.assertIsNone(result['preset_id'])

    def test_preset_resolves_seed(self):
        result = normalize_appearance(
            {
                'version': 1,
                'mode': 'light',
                'preset_id': 'mgask_default',
            }
        )
        self.assertEqual(result['seed_color'], '#990404')
