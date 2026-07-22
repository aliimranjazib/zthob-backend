from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.serializers import UserProfileSerializer
from apps.core.phone_utils import display_user_label, format_phone_for_display


User = get_user_model()


class PhoneDisplayUtilsTest(TestCase):
    def test_format_saudi_local_phone_to_e164(self):
        self.assertEqual(format_phone_for_display('0501234567'), '+966501234567')

    def test_format_already_e164_phone(self):
        self.assertEqual(format_phone_for_display('+966501234567'), '+966501234567')

    def test_display_user_label_prefers_name_then_phone(self):
        user = User.objects.create_user(
            username='user_0501234567',
            phone='0501234567',
            password='testpass123',
        )
        self.assertEqual(display_user_label(user), '+966501234567')

        user.first_name = 'Ali'
        user.last_name = 'Ahmed'
        user.save(update_fields=['first_name', 'last_name'])
        self.assertEqual(display_user_label(user), 'Ali Ahmed')


class PhoneDisplayAPITest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='phone_display_user',
            phone='0509876543',
            password='testpass123',
            role='USER',
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_profile_returns_formatted_phone(self):
        response = self.client.get('/api/accounts/profile/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['data']['phone'], '+966509876543')

    def test_user_profile_serializer_formats_phone(self):
        data = UserProfileSerializer(self.user).data
        self.assertEqual(data['phone'], '+966509876543')
