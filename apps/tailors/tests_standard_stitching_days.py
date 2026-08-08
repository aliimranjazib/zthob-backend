from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.tailors.models import TailorProfile


User = get_user_model()


@override_settings(
    SECURE_SSL_REDIRECT=False,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}},
)
class StandardStitchingDaysTest(TestCase):
    def setUp(self):
        self.tailor = User.objects.create_user(
            username='stitching_days_tailor',
            phone='0511111120',
            password='testpass123',
            role='TAILOR',
        )
        self.profile, _ = TailorProfile.objects.get_or_create(
            user=self.tailor,
            defaults={'shop_name': 'Stitching Days Shop', 'shop_status': True},
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.tailor)

    def test_profile_returns_standard_stitching_days(self):
        self.client.patch(
            '/api/tailors/profile/',
            {'standard_stitching_days': 7},
            format='json',
        )

        response = self.client.get('/api/tailors/profile/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['standard_stitching_days'], 7)

    def test_profile_can_update_standard_stitching_days(self):
        response = self.client.patch(
            '/api/tailors/profile/',
            {'standard_stitching_days': 10},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.standard_stitching_days, 10)
        self.assertEqual(response.data['data']['standard_stitching_days'], 10)

    def test_profile_rejects_out_of_range_standard_stitching_days(self):
        response = self.client.patch(
            '/api/tailors/profile/',
            {'standard_stitching_days': 0},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_config_includes_standard_stitching_days_for_authenticated_tailor(self):
        self.client.patch(
            '/api/tailors/profile/',
            {'standard_stitching_days': 5},
            format='json',
        )

        response = self.client.get('/api/tailors/config/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data['data']
        self.assertEqual(data['standard_stitching_days'], 5)
        self.assertEqual(data['standard_stitching_days_min'], 1)
        self.assertEqual(data['standard_stitching_days_max'], 30)

    def test_profile_rejects_standard_stitching_days_above_max(self):
        response = self.client.patch(
            '/api/tailors/profile/',
            {'standard_stitching_days': 31},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_config_returns_null_standard_stitching_days_when_anonymous(self):
        anonymous_client = APIClient()
        response = anonymous_client.get('/api/tailors/config/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data['data']['standard_stitching_days'])
        self.assertEqual(response.data['data']['standard_stitching_days_min'], 1)
        self.assertEqual(response.data['data']['standard_stitching_days_max'], 30)
