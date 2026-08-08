from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.customers.models import Address
from apps.orders.models import Order, OrderItem, OrderStatusHistory
from apps.tailors.models import Fabric, FabricCategory, TailorProfile


User = get_user_model()


@override_settings(
    SECURE_SSL_REDIRECT=False,
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    },
)
class RejectOrderActionTest(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(
            username='reject_customer',
            email='reject_customer@example.com',
            password='testpass123',
            role='USER',
        )
        self.tailor = User.objects.create_user(
            username='reject_tailor',
            email='reject_tailor@example.com',
            password='testpass123',
            role='TAILOR',
        )
        self.tailor_profile, _ = TailorProfile.objects.get_or_create(
            user=self.tailor,
            defaults={'shop_name': 'Reject Tailor', 'shop_status': True},
        )
        self.address = Address.objects.create(
            user=self.customer,
            street='123 Test St',
            city='Riyadh',
            country='Saudi Arabia',
        )
        self.category = FabricCategory.objects.create(name='Fabric', slug='fabric')
        self.fabric = Fabric.objects.create(
            tailor=self.tailor_profile,
            category=self.category,
            name='Reject Fabric',
            price=Decimal('100.00'),
            stock=10,
            is_active=True,
        )
        self.tailor_client = APIClient()
        self.tailor_client.force_authenticate(user=self.tailor)

    def _create_order(self, **overrides):
        defaults = {
            'customer': self.customer,
            'tailor': self.tailor,
            'order_type': 'fabric_only',
            'service_mode': 'home_delivery',
            'payment_method': 'cod',
            'payment_status': 'pending',
            'status': 'pending',
            'tailor_status': 'none',
            'delivery_address': self.address,
            'subtotal': Decimal('100.00'),
            'tax_amount': Decimal('15.00'),
            'delivery_fee': Decimal('20.00'),
            'total_amount': Decimal('135.00'),
        }
        defaults.update(overrides)
        order = Order.objects.create(**defaults)
        OrderItem.objects.create(
            order=order,
            fabric=self.fabric,
            quantity=1,
            unit_price=Decimal('100.00'),
            total_price=Decimal('100.00'),
        )
        return order

    def test_tailor_config_includes_order_rejection_reasons(self):
        response = self.tailor_client.get(
            '/api/tailors/config/',
            HTTP_ACCEPT_LANGUAGE='ar',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        reasons = response.data['data']['order_rejection_reasons']
        self.assertGreaterEqual(len(reasons), 1)
        self.assertEqual(reasons[0]['key'], 'out_of_capacity')
        self.assertIn('label', reasons[0])

    def test_cod_pending_order_shows_reject_action(self):
        order = self._create_order()
        detail = self.tailor_client.get(f'/api/orders/tailor/{order.id}/')
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        action_keys = [
            action['key']
            for action in detail.data['data']['status_info']['available_actions']
        ]
        self.assertIn('reject_order', action_keys)
        self.assertIn('accept_order', action_keys)

    @patch('apps.notifications.services.NotificationService.send_order_rejected_by_tailor_notification')
    def test_tailor_can_reject_cod_order_with_predefined_reason(self, mock_notify):
        order = self._create_order()
        response = self.tailor_client.post(
            f'/api/orders/{order.id}/action/',
            {
                'action': 'reject_order',
                'role': 'TAILOR',
                'data': {'rejection_reason_code': 'out_of_capacity'},
            },
            format='json',
            HTTP_ACCEPT_LANGUAGE='ar',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        order.refresh_from_db()
        self.assertEqual(order.status, 'cancelled')
        self.assertEqual(order.rejection_reason_code, 'out_of_capacity')
        self.assertTrue(order.rejection_reason)
        self.assertEqual(order.rejected_by, self.tailor)
        self.assertEqual(response.data['data']['status'], 'cancelled')
        self.assertEqual(response.data['data']['rejection_reason_code'], 'out_of_capacity')
        mock_notify.assert_called_once()
        history = OrderStatusHistory.objects.filter(order=order).latest('created_at')
        self.assertIn('Rejected by tailor', history.notes)

    @patch('apps.notifications.services.NotificationService.send_order_rejected_by_tailor_notification')
    def test_tailor_can_reject_cod_order_with_custom_reason_only(self, mock_notify):
        order = self._create_order()
        response = self.tailor_client.post(
            f'/api/orders/{order.id}/action/',
            {
                'action': 'reject_order',
                'role': 'TAILOR',
                'data': {
                    'rejection_reason': 'Cannot complete this order before Eid deadline',
                },
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        order.refresh_from_db()
        self.assertEqual(order.status, 'cancelled')
        self.assertEqual(
            order.rejection_reason,
            'Cannot complete this order before Eid deadline',
        )
        mock_notify.assert_called_once()

    def test_reject_credit_card_order_is_blocked(self):
        order = self._create_order(payment_method='credit_card')
        response = self.tailor_client.post(
            f'/api/orders/{order.id}/action/',
            {
                'action': 'reject_order',
                'role': 'TAILOR',
                'data': {'rejection_reason_code': 'out_of_capacity'},
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        order.refresh_from_db()
        self.assertEqual(order.status, 'pending')

    def test_reject_after_accept_is_blocked(self):
        order = self._create_order(tailor_status='accepted', status='confirmed')
        response = self.tailor_client.post(
            f'/api/orders/{order.id}/action/',
            {
                'action': 'reject_order',
                'role': 'TAILOR',
                'data': {'rejection_reason_code': 'out_of_capacity'},
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reject_other_reason_requires_details(self):
        order = self._create_order()
        response = self.tailor_client.post(
            f'/api/orders/{order.id}/action/',
            {
                'action': 'reject_order',
                'role': 'TAILOR',
                'data': {'rejection_reason_code': 'other'},
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reject_without_reason_is_blocked(self):
        order = self._create_order()
        response = self.tailor_client.post(
            f'/api/orders/{order.id}/action/',
            {
                'action': 'reject_order',
                'role': 'TAILOR',
                'data': {},
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('apps.notifications.services.NotificationService.send_notification')
    def test_reject_notification_uses_arabic_override(self, mock_send):
        order = self._create_order()
        from apps.notifications.services import NotificationService

        NotificationService.send_order_rejected_by_tailor_notification(
            order,
            'المتجر ممتلئ بالطلبات حالياً',
            self.tailor,
        )

        self.assertEqual(mock_send.call_count, 2)
        for call in mock_send.call_args_list:
            self.assertEqual(call.kwargs.get('language_override'), 'ar')

    def _reject_order(self, order):
        with patch(
            'apps.notifications.services.NotificationService.send_order_rejected_by_tailor_notification'
        ):
            response = self.tailor_client.post(
                f'/api/orders/{order.id}/action/',
                {
                    'action': 'reject_order',
                    'role': 'TAILOR',
                    'data': {'rejection_reason_code': 'fabric_unavailable'},
                },
                format='json',
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response

    def test_rejected_order_removed_from_available_orders(self):
        order = self._create_order()
        self._reject_order(order)
        list_response = self.tailor_client.get('/api/orders/tailor/available-orders/')
        order_ids = [item['id'] for item in list_response.data['data']]
        self.assertNotIn(order.id, order_ids)

    def test_rejected_order_excluded_from_my_orders_with_tailor_status_none(self):
        order = self._create_order()
        self._reject_order(order)
        list_response = self.tailor_client.get(
            '/api/orders/tailor/my-orders/',
            {
                'payment_status': '',
                'tailor_status': 'none',
                'service_mode': 'home_delivery',
            },
        )
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        order_ids = [item['id'] for item in list_response.data['data']]
        self.assertNotIn(order.id, order_ids)

    def test_rejected_order_excluded_from_paid_orders(self):
        order = self._create_order()
        self._reject_order(order)
        list_response = self.tailor_client.get('/api/orders/tailor/paid-orders/')
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        order_ids = [item['id'] for item in list_response.data['data']]
        self.assertNotIn(order.id, order_ids)

    def test_my_orders_can_still_filter_cancelled_when_requested(self):
        order = self._create_order()
        self._reject_order(order)
        list_response = self.tailor_client.get(
            '/api/orders/tailor/my-orders/',
            {'status': 'cancelled'},
        )
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        order_ids = [item['id'] for item in list_response.data['data']]
        self.assertIn(order.id, order_ids)
