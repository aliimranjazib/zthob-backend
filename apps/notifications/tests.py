from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient


User = get_user_model()


@override_settings(
    SECURE_SSL_REDIRECT=False,
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    },
)
class TestNotificationEndpointRoleScopeTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def _create_user(self, role):
        return User.objects.create_user(
            username=f'{role.lower()}_user',
            phone=f'05000000{len(role)}{len(role)}',
            password='testpass123',
            role=role,
        )

    def _assert_test_notification_uses_app_role(self, url, user_role, expected_app_role):
        user = self._create_user(user_role)
        self.client.force_authenticate(user=user)

        with patch('apps.notifications.services.NotificationService.send_notification', return_value=True) as mock_send:
            response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send.assert_called_once()
        self.assertEqual(mock_send.call_args.kwargs['user'], user)
        self.assertEqual(mock_send.call_args.kwargs['app_role'], expected_app_role)

    def test_customer_test_notification_targets_customer_app_tokens(self):
        self._assert_test_notification_uses_app_role(
            '/api/notifications/test-customer/',
            'USER',
            'CUSTOMER',
        )

    def test_tailor_test_notification_targets_tailor_app_tokens(self):
        self._assert_test_notification_uses_app_role(
            '/api/notifications/test-tailor/',
            'TAILOR',
            'TAILOR',
        )

    def test_rider_test_notification_targets_rider_app_tokens(self):
        self._assert_test_notification_uses_app_role(
            '/api/notifications/test-rider/',
            'RIDER',
            'RIDER',
        )

    def test_customer_cannot_hit_tailor_test_notification(self):
        user = self._create_user('USER')
        self.client.force_authenticate(user=user)

        with patch('apps.notifications.services.NotificationService.send_notification') as mock_send:
            response = self.client.post('/api/notifications/test-tailor/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        mock_send.assert_not_called()
