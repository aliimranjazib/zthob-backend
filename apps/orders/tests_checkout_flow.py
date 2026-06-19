from decimal import Decimal
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.customers.models import Address
from apps.orders.models import CheckoutSession, Order, OrderPayment
from apps.tailors.models import Fabric, FabricCategory, TailorProfile


User = get_user_model()


@override_settings(
    SECURE_SSL_REDIRECT=False,
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }
)
class CheckoutFlowTest(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(
            username='checkout_customer',
            email='checkout_customer@example.com',
            password='testpass123',
            role='USER',
        )
        self.tailor = User.objects.create_user(
            username='checkout_tailor',
            email='checkout_tailor@example.com',
            password='testpass123',
            role='TAILOR',
        )
        self.tailor_profile, _ = TailorProfile.objects.get_or_create(
            user=self.tailor,
            defaults={'shop_name': 'Checkout Tailor', 'shop_status': True},
        )
        self.category = FabricCategory.objects.create(name='Fabric', slug='checkout-fabric')
        self.fabric = Fabric.objects.create(
            tailor=self.tailor_profile,
            category=self.category,
            name='Checkout Fabric',
            price=Decimal('100.00'),
            stock=10,
            is_active=True,
        )
        self.address = Address.objects.create(
            user=self.customer,
            street='123 Checkout St',
            city='Riyadh',
            country='Saudi Arabia',
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.customer)

    def _checkout_payload(self):
        return {
            'tailor': self.tailor.id,
            'order_type': 'fabric_only',
            'service_mode': 'home_delivery',
            'payment_method': 'credit_card',
            'delivery_address': self.address.id,
            'items': [
                {'fabric': self.fabric.id, 'quantity': 1, 'measurements': {}}
            ],
        }

    def _create_checkout(self):
        response = self.client.post(
            '/api/orders/checkout/',
            data=self._checkout_payload(),
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return response.data['data']['bookingUniqueKey']

    def test_checkout_creates_draft_not_order(self):
        response = self.client.post(
            '/api/orders/checkout/',
            data=self._checkout_payload(),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['data']['bookingUniqueKey'].startswith('chk_'))
        self.assertEqual(Order.objects.count(), 0)
        self.fabric.refresh_from_db()
        self.assertEqual(self.fabric.stock, 10)
        self.assertIn('total_amount', response.data['data']['pricing_summary'])

    def test_cod_create_order_from_checkout_is_pending_payment(self):
        booking_key = self._create_checkout()

        response = self.client.post(
            '/api/orders/checkout/create-order/',
            data={'bookingUniqueKey': booking_key, 'payment_method': 'cod'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        order = Order.objects.get()
        self.assertEqual(order.payment_method, 'cod')
        self.assertEqual(order.payment_status, 'pending')
        self.assertEqual(order.payment_plan, 'pay_later')
        self.assertEqual(order.paid_amount, Decimal('0.00'))
        self.assertEqual(order.remaining_amount, order.total_amount)
        self.assertIsNone(order.payment_reference)
        self.fabric.refresh_from_db()
        self.assertEqual(self.fabric.stock, 9)

    def test_credit_card_requires_payment_reference(self):
        booking_key = self._create_checkout()

        response = self.client.post(
            '/api/orders/checkout/create-order/',
            data={'bookingUniqueKey': booking_key, 'payment_method': 'credit_card'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Order.objects.count(), 0)

    def test_credit_card_create_order_from_checkout_is_paid(self):
        booking_key = self._create_checkout()

        response = self.client.post(
            '/api/orders/checkout/create-order/',
            data={
                'bookingUniqueKey': booking_key,
                'payment_method': 'credit_card',
                'payment_reference': 'txn_checkout_001',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        order = Order.objects.get()
        checkout = CheckoutSession.objects.get(booking_unique_key=booking_key)
        self.assertEqual(order.payment_method, 'credit_card')
        self.assertEqual(order.payment_status, 'paid')
        self.assertEqual(order.payment_plan, 'full')
        self.assertEqual(order.paid_amount, order.total_amount)
        self.assertEqual(order.remaining_amount, Decimal('0.00'))
        self.assertEqual(order.payment_reference, 'txn_checkout_001')
        self.assertEqual(OrderPayment.objects.filter(order=order, payment_type='full_payment').count(), 1)
        self.assertEqual(checkout.status, 'order_created')
        self.assertEqual(checkout.order, order)

    def test_checkout_returns_backend_payment_options(self):
        response = self.client.post(
            '/api/orders/checkout/',
            data=self._checkout_payload(),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        option_keys = [
            option['key']
            for option in response.data['data']['pricing_summary']['payment_options']
        ]
        self.assertIn('full', option_keys)
        self.assertIn('advance_50', option_keys)
        self.assertIn('pay_later', option_keys)

    def test_partial_payment_create_order_from_checkout_is_partially_paid(self):
        booking_key = self._create_checkout()

        response = self.client.post(
            '/api/orders/checkout/create-order/',
            data={
                'bookingUniqueKey': booking_key,
                'payment_method': 'credit_card',
                'payment_option': 'advance_50',
                'payment_reference': 'txn_checkout_deposit_001',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        order = Order.objects.get()
        checkout = CheckoutSession.objects.get(booking_unique_key=booking_key)
        self.assertEqual(order.payment_status, 'partially_paid')
        self.assertEqual(order.payment_plan, 'partial')
        self.assertEqual(order.payment_option, 'advance_50')
        self.assertEqual(order.paid_amount, order.deposit_amount)
        self.assertGreater(order.remaining_amount, Decimal('0.00'))
        self.assertEqual(checkout.payment_plan, 'partial')
        self.assertEqual(checkout.payment_option, 'advance_50')
        self.assertEqual(OrderPayment.objects.filter(order=order, payment_type='deposit').count(), 1)

    def test_unavailable_payment_option_is_rejected(self):
        booking_key = self._create_checkout()

        response = self.client.post(
            '/api/orders/checkout/create-order/',
            data={
                'bookingUniqueKey': booking_key,
                'payment_method': 'credit_card',
                'payment_option': 'advance_30',
                'payment_reference': 'txn_checkout_invalid_option',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Order.objects.count(), 0)

    def test_repeating_create_order_for_same_checkout_returns_existing_order(self):
        booking_key = self._create_checkout()
        payload = {
            'bookingUniqueKey': booking_key,
            'payment_method': 'credit_card',
            'payment_reference': 'txn_checkout_repeat',
        }

        first_response = self.client.post('/api/orders/checkout/create-order/', data=payload, format='json')
        second_response = self.client.post('/api/orders/checkout/create-order/', data=payload, format='json')

        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        self.assertEqual(Order.objects.count(), 1)
        self.fabric.refresh_from_db()
        self.assertEqual(self.fabric.stock, 9)

    def test_used_payment_reference_cannot_create_another_order(self):
        first_booking_key = self._create_checkout()
        response = self.client.post(
            '/api/orders/checkout/create-order/',
            data={
                'bookingUniqueKey': first_booking_key,
                'payment_method': 'credit_card',
                'payment_reference': 'txn_duplicate_ref',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        second_booking_key = self._create_checkout()
        response = self.client.post(
            '/api/orders/checkout/create-order/',
            data={
                'bookingUniqueKey': second_booking_key,
                'payment_method': 'credit_card',
                'payment_reference': 'txn_duplicate_ref',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Order.objects.count(), 1)

    def test_expired_checkout_cannot_create_order(self):
        booking_key = self._create_checkout()
        CheckoutSession.objects.filter(booking_unique_key=booking_key).update(
            expires_at=timezone.now() - timezone.timedelta(minutes=1)
        )

        response = self.client.post(
            '/api/orders/checkout/create-order/',
            data={'bookingUniqueKey': booking_key, 'payment_method': 'cod'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Order.objects.count(), 0)

    @override_settings(
        ALINMAPAY_TERMINAL_ID='TERM123',
        ALINMAPAY_TERMINAL_PASSWORD='term-password',
        ALINMAPAY_MERCHANT_KEY='00112233445566778899aabbccddeeff',
        ALINMAPAY_REQUEST_URL='https://example.com/pay-request',
        ALINMAPAY_RECEIPT_BASE_URL='https://app.mgask.net',
    )
    @patch('apps.orders.alinma.requests.post')
    def test_initiate_alinma_payment_returns_hosted_payment_url(self, mock_post):
        booking_key = self._create_checkout()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'responseCode': '000',
            'transactionId': '2610414541753672882',
            'paymentLink': {'linkUrl': 'https://pg.alinmapay.com.sa/SB_Transactions/direct.htm?paymentId='},
        }
        mock_post.return_value = mock_response

        response = self.client.post(
            '/api/orders/checkout/initiate-payment/',
            data={'bookingUniqueKey': booking_key, 'payment_option': 'advance_50'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['bookingUniqueKey'], booking_key)
        self.assertEqual(response.data['data']['payment_option'], 'advance_50')
        self.assertEqual(
            response.data['data']['payment_url'],
            'https://pg.alinmapay.com.sa/SB_Transactions/direct.htm?paymentId=2610414541753672882'
        )
        checkout = CheckoutSession.objects.get(booking_unique_key=booking_key)
        self.assertEqual(checkout.payment_method, 'credit_card')
        self.assertEqual(checkout.payment_option, 'advance_50')
        self.assertEqual(checkout.status, 'payment_initiated')

    @override_settings(
        ALINMAPAY_TERMINAL_ID='TERM123',
        ALINMAPAY_TERMINAL_PASSWORD='term-password',
        ALINMAPAY_MERCHANT_KEY='00112233445566778899aabbccddeeff',
        ALINMAPAY_REQUEST_URL='https://example.com/pay-request',
    )
    @patch('apps.notifications.services.NotificationService.send_payment_status_notification')
    @patch('apps.notifications.services.NotificationService.send_order_status_notification')
    @patch('apps.orders.views.verify_callback_signature', return_value=True)
    @patch('apps.orders.views.parse_callback_payload')
    def test_alinma_callback_creates_paid_order(
        self,
        mock_parse_callback_payload,
        _mock_verify,
        mock_send_order_status_notification,
        mock_send_payment_status_notification,
    ):
        booking_key = self._create_checkout()
        checkout = CheckoutSession.objects.get(booking_unique_key=booking_key)
        checkout.payment_option = 'full'
        checkout.payment_method = 'credit_card'
        checkout.save(update_fields=['payment_option', 'payment_method'])

        mock_parse_callback_payload.return_value = {
            'transactionId': 'alinma_txn_001',
            'responseCode': '000',
            'result': 'SUCCESS',
            'signature': 'valid-signature',
            'amountDetails': {'amount': '100.00'},
            'orderDetails': {'orderId': booking_key},
        }

        response = self.client.post(
            '/api/orders/checkout/alinma/callback/',
            data={'data': 'encrypted-payload-placeholder'},
        )

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertIn('status=success', response['Location'])
        self.assertIn(f'booking_key={booking_key}', response['Location'])
        order = Order.objects.get()
        checkout.refresh_from_db()
        self.assertEqual(order.payment_method, 'credit_card')
        self.assertEqual(order.payment_status, 'paid')
        self.assertEqual(order.payment_reference, 'alinma_txn_001')
        self.assertEqual(checkout.status, 'order_created')
        self.assertEqual(Order.objects.count(), 1)
        mock_send_order_status_notification.assert_called_once()
        mock_send_payment_status_notification.assert_called_once_with(
            order=order,
            old_status='pending',
            new_status='paid',
        )

    @override_settings(
        ALINMAPAY_TERMINAL_ID='TERM123',
        ALINMAPAY_TERMINAL_PASSWORD='term-password',
        ALINMAPAY_MERCHANT_KEY='00112233445566778899aabbccddeeff',
        ALINMAPAY_REQUEST_URL='https://example.com/pay-request',
    )
    @patch('apps.orders.views.verify_callback_signature', return_value=True)
    @patch('apps.orders.views.parse_callback_payload')
    def test_alinma_callback_failure_marks_checkout_failed(self, mock_parse_callback_payload, _mock_verify):
        booking_key = self._create_checkout()
        checkout = CheckoutSession.objects.get(booking_unique_key=booking_key)
        checkout.payment_option = 'full'
        checkout.payment_method = 'credit_card'
        checkout.save(update_fields=['payment_option', 'payment_method'])

        mock_parse_callback_payload.return_value = {
            'transactionId': 'alinma_txn_failed',
            'responseCode': '500',
            'result': 'FAILED',
            'signature': 'valid-signature',
            'amountDetails': {'amount': '100.00'},
            'orderDetails': {'orderId': booking_key},
        }

        response = self.client.post(
            '/api/orders/checkout/alinma/callback/',
            data={'data': 'encrypted-payload-placeholder'},
        )

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertIn('status=failed', response['Location'])
        self.assertIn(f'booking_key={booking_key}', response['Location'])
        checkout.refresh_from_db()
        self.assertEqual(checkout.status, 'payment_failed')
        self.assertEqual(checkout.payment_reference, 'alinma_txn_failed')
        self.assertEqual(Order.objects.count(), 0)
