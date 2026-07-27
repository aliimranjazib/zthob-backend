from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


class ProfileLanguageTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='urdu_user',
            password='testpass123',
            phone='0501234567',
            language='ar',
        )
        self.client.force_authenticate(user=self.user)
        self.profile_url = reverse('accounts:user-profile')

    def test_update_profile_language_to_urdu(self):
        response = self.client.put(
            self.profile_url,
            {'language': 'ur'},
            format='json',
            HTTP_ACCEPT_LANGUAGE='ur',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['message'], 'پروفائل کامیابی سے اپ ڈیٹ ہو گئی')
        self.assertEqual(response.data['data']['language'], 'ur')
        self.user.refresh_from_db()
        self.assertEqual(self.user.language, 'ur')

    def test_invalid_profile_language_rejected(self):
        response = self.client.put(
            self.profile_url,
            {'language': 'fr'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])

    def test_profile_fetch_translates_to_urdu(self):
        self.user.language = 'ur'
        self.user.save(update_fields=['language'])
        response = self.client.get(
            self.profile_url,
            HTTP_ACCEPT_LANGUAGE='ur',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'پروفائل کامیابی سے حاصل ہو گئی')
