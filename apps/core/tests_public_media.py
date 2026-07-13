import os
import tempfile

from django.test import TestCase
from rest_framework.test import APIRequestFactory, APIClient

from apps.core.media_utils import build_public_media_url, media_path_from_url


class MediaUtilsTests(TestCase):
    def test_media_path_from_relative_url(self):
        self.assertEqual(
            media_path_from_url('custom_styles/2026/06/test.png'),
            'custom_styles/2026/06/test.png',
        )

    def test_media_path_from_media_prefixed_path(self):
        self.assertEqual(
            media_path_from_url('/media/tailor_profiles/shop_images/shop.jpg'),
            'tailor_profiles/shop_images/shop.jpg',
        )

    def test_media_path_from_absolute_url(self):
        self.assertEqual(
            media_path_from_url(
                'https://prod.mgask.net/media/custom_styles/2026/06/test.png'
            ),
            'custom_styles/2026/06/test.png',
        )

    def test_build_public_media_url_with_request(self):
        factory = APIRequestFactory()
        request = factory.get('/api/customization/categories/')
        request.META['HTTP_HOST'] = 'prod.mgask.net'
        request.META['wsgi.url_scheme'] = 'https'

        url = build_public_media_url(
            request,
            '/media/custom_styles/2026/06/test.png',
        )
        self.assertEqual(
            url,
            'https://prod.mgask.net/api/media/custom_styles/2026/06/test.png',
        )


class PublicMediaServeViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.media_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.media_dir, 'custom_styles', 'test.png')
        os.makedirs(os.path.dirname(self.test_file), exist_ok=True)
        with open(self.test_file, 'wb') as handle:
            handle.write(b'\x89PNG\r\n\x1a\n')

    def test_serves_media_file(self):
        with self.settings(MEDIA_ROOT=self.media_dir):
            response = self.client.get('/api/media/custom_styles/test.png')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response['Content-Type'].startswith('image/'))

    def test_rejects_path_traversal(self):
        with self.settings(MEDIA_ROOT=self.media_dir):
            response = self.client.get('/api/media/../settings.py')
        self.assertEqual(response.status_code, 404)

    def test_includes_cors_header_for_tailor_origin(self):
        with self.settings(MEDIA_ROOT=self.media_dir):
            response = self.client.get(
                '/api/media/custom_styles/test.png',
                HTTP_ORIGIN='https://tailor.mgask.net',
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Access-Control-Allow-Origin'],
            'https://tailor.mgask.net',
        )
