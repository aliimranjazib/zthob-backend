"""Tests for admin messaging center (Phase 1)."""
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from apps.messaging.models import AdminMessageDelivery, AdminOutboundMessage
from apps.messaging.services import process_admin_message, resolve_recipients

User = get_user_model()


@override_settings(
    TAQNYAT_BEARER_TOKEN='test_token',
    TAQNYAT_SENDER_NAME='TestSender',
)
class MessagingServiceTestCase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin_user',
            password='testpass123',
            role='ADMIN',
            is_staff=True,
            is_superuser=True,
        )
        self.tailor = User.objects.create_user(
            username='tailor_user',
            password='testpass123',
            role='TAILOR',
            phone='0501234567',
            phone_verified=True,
        )
        self.customer = User.objects.create_user(
            username='customer_user',
            password='testpass123',
            role='USER',
            phone='0509876543',
            phone_verified=True,
        )

    def _create_message(self, **overrides):
        defaults = {
            'sent_by': self.admin,
            'channel': 'sms',
            'audience_type': 'single',
            'target_user': self.tailor,
            'body': 'Your shop has been approved on Mgask.',
            'status': 'queued',
        }
        defaults.update(overrides)
        return AdminOutboundMessage.objects.create(**defaults)

    def test_resolve_recipients_single(self):
        message = self._create_message(audience_type='single', target_user=self.tailor)
        recipients = resolve_recipients(message)
        self.assertEqual([user.pk for user in recipients], [self.tailor.pk])

    def test_resolve_recipients_role(self):
        message = self._create_message(
            audience_type='role',
            target_role='TAILOR',
            target_user=None,
        )
        recipients = resolve_recipients(message)
        self.assertEqual([user.pk for user in recipients], [self.tailor.pk])

    def test_resolve_recipients_selected(self):
        message = self._create_message(
            audience_type='selected',
            target_user=None,
        )
        message.recipients.set([self.customer, self.tailor])
        recipients = resolve_recipients(message)
        self.assertEqual(sorted(user.pk for user in recipients), sorted([self.customer.pk, self.tailor.pk]))

    @patch('apps.messaging.services.TaqnyatSMSService.send_sms')
    def test_process_admin_message_sms_success(self, mock_send_sms):
        mock_send_sms.return_value = (True, 'ok', 'msg-123')
        message = self._create_message()

        result = process_admin_message(message.pk)

        self.assertTrue(result)
        message.refresh_from_db()
        self.assertEqual(message.status, 'completed')
        self.assertEqual(message.total_recipients, 1)
        self.assertEqual(message.sent_count, 1)
        self.assertEqual(message.failed_count, 0)

        delivery = AdminMessageDelivery.objects.get(message=message, user=self.tailor)
        self.assertEqual(delivery.status, 'sent')
        self.assertEqual(delivery.sms_status, 'sent')
        self.assertEqual(delivery.provider_message_id, 'msg-123')
        mock_send_sms.assert_called_once()

    @patch('apps.messaging.services.TaqnyatSMSService.send_sms')
    def test_process_admin_message_sms_missing_phone(self, mock_send_sms):
        self.tailor.phone = ''
        self.tailor.save(update_fields=['phone'])
        message = self._create_message()

        process_admin_message(message.pk)

        message.refresh_from_db()
        self.assertEqual(message.failed_count, 1)
        delivery = AdminMessageDelivery.objects.get(message=message, user=self.tailor)
        self.assertEqual(delivery.status, 'skipped')
        self.assertEqual(delivery.sms_status, 'skipped')
        mock_send_sms.assert_not_called()

    @patch('apps.messaging.services.NotificationService.send_notification')
    @patch('apps.messaging.services.TaqnyatSMSService.send_sms')
    def test_process_admin_message_both_channels(self, mock_send_sms, mock_push):
        mock_send_sms.return_value = (True, 'ok', 'msg-456')
        mock_push.return_value = True
        message = self._create_message(channel='both', title='Shop approved')

        process_admin_message(message.pk)

        delivery = AdminMessageDelivery.objects.get(message=message, user=self.tailor)
        self.assertEqual(delivery.status, 'sent')
        self.assertEqual(delivery.sms_status, 'sent')
        self.assertEqual(delivery.push_status, 'sent')
        mock_send_sms.assert_called_once()
        mock_push.assert_called_once()


@override_settings(
    TAQNYAT_BEARER_TOKEN='test_token',
    TAQNYAT_SENDER_NAME='TestSender',
)
class TaqnyatSendSmsTestCase(TestCase):
    @patch('apps.core.taqnyat_service.urllib.request.urlopen')
    def test_send_sms_success(self, mock_urlopen):
        from apps.core.taqnyat_service import TaqnyatSMSService

        mock_response = mock_urlopen.return_value.__enter__.return_value
        mock_response.read.return_value = b'{"statusCode":201,"messageId":"abc-123"}'

        success, message, message_id = TaqnyatSMSService.send_sms('0501234567', 'Hello tailor')

        self.assertTrue(success)
        self.assertEqual(message_id, 'abc-123')
        self.assertIn('messageId', message)

    def test_send_sms_requires_body(self):
        from apps.core.taqnyat_service import TaqnyatSMSService

        success, message, message_id = TaqnyatSMSService.send_sms('0501234567', '   ')
        self.assertFalse(success)
        self.assertIsNone(message_id)
        self.assertIn('required', message.lower())
