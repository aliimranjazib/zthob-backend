"""CORS preflight for custom session headers used by web clients."""

from django.test import TestCase, override_settings


@override_settings(
    SECURE_SSL_REDIRECT=False,
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    },
)
class CorsAppEntryHeaderTest(TestCase):
    def test_preflight_allows_x_app_entry_for_tailor_origin(self):
        response = self.client.options(
            '/api/v2/auth/phone-login/',
            HTTP_ORIGIN='https://tailor.mgask.net',
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='POST',
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS='content-type,x-app-entry',
        )
        self.assertEqual(response.status_code, 200)
        allow_headers = response.get('Access-Control-Allow-Headers', '').lower()
        self.assertIn('x-app-entry', allow_headers)
        self.assertEqual(
            response.get('Access-Control-Allow-Origin'),
            'https://tailor.mgask.net',
        )

    def test_preflight_does_not_reflect_unlisted_origin(self):
        response = self.client.options(
            '/api/v2/auth/phone-login/',
            HTTP_ORIGIN='https://evil.example',
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='POST',
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS='x-app-entry',
        )
        self.assertNotEqual(
            response.get('Access-Control-Allow-Origin'),
            'https://evil.example',
        )
