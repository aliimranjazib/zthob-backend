import base64
import hashlib
import hmac
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.customers.models import Address
from apps.orders.models import CheckoutPaymentAttempt, MyFatoorahWebhookEvent, Order
from apps.orders.myfatoorah import PaymentDetails
from apps.tailors.models import Fabric, FabricCategory, TailorProfile


User = get_user_model()


@override_settings(
    SECURE_SSL_REDIRECT=False,
    MYFATOORAH_API_KEY='test-api-key',
    MYFATOORAH_WEBHOOK_SECRET='test-webhook-secret',
    MYFATOORAH_API_BASE_URL='https://apitest.myfatoorah.com',
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}},
)
class MyFatoorahPaymentFlowTest(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(
            username='myfatoorah_customer',
            email='customer@example.com',
            password='testpass123',
            role='USER',
        )
        tailor = User.objects.create_user(
            username='myfatoorah_tailor',
            email='tailor@example.com',
            password='testpass123',
            role='TAILOR',
        )
        tailor_profile, _ = TailorProfile.objects.get_or_create(
            user=tailor,
            defaults={'shop_name': 'MyFatoorah Tailor', 'shop_status': True},
        )
        category = FabricCategory.objects.create(name='MF Fabric', slug='mf-fabric')
        self.fabric = Fabric.objects.create(
            tailor=tailor_profile,
            category=category,
            name='MF Fabric',
            price=Decimal('100.00'),
            stock=10,
            is_active=True,
        )
        self.address = Address.objects.create(
            user=self.customer,
            street='Riyadh Street',
            city='Riyadh',
            country='Saudi Arabia',
        )
        self.tailor = tailor
        self.client = APIClient()
        self.client.force_authenticate(user=self.customer)

    def _create_checkout(self):
        response = self.client.post(
            '/api/orders/checkout/',
            data={
                'tailor': self.tailor.id,
                'order_type': 'fabric_only',
                'service_mode': 'home_delivery',
                'payment_method': 'credit_card',
                'delivery_address': self.address.id,
                'items': [{'fabric': self.fabric.id, 'quantity': 1, 'measurements': {}}],
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return response.data['data']['bookingUniqueKey']

    def _prepare(self, booking_key, key='idem-1', option='full'):
        response = self.client.post(
            '/api/orders/checkout/myfatoorah/prepare/',
            data={
                'bookingUniqueKey': booking_key,
                'payment_option': option,
                'idempotency_key': key,
            },
            format='json',
        )
        self.assertIn(response.status_code, {status.HTTP_200_OK, status.HTTP_201_CREATED})
        return response

    def _details(self, attempt, **overrides):
        values = {
            'invoice_id': '900001',
            'invoice_status': 'PAID',
            'invoice_value': attempt.expected_amount,
            'currency': 'SAR',
            'customer_reference': attempt.attempt_reference,
            'user_defined_field': attempt.attempt_reference,
            'transaction_status': 'SUCCESS',
            'payment_id': '0707900001001',
            'payment_method': 'MADA',
            'gateway_reference': 'gateway-ref-1',
        }
        values.update(overrides)
        return PaymentDetails(**values)

    def test_prepare_uses_backend_amount_and_is_idempotent(self):
        booking_key = self._create_checkout()
        first = self._prepare(booking_key)
        second = self._prepare(booking_key)

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(
            first.data['data']['attempt_reference'],
            second.data['data']['attempt_reference'],
        )
        self.assertEqual(first.data['data']['currency'], 'SAR')
        self.assertEqual(CheckoutPaymentAttempt.objects.count(), 1)

    @patch('apps.orders.myfatoorah_views.get_payment_status')
    def test_confirm_verifies_and_creates_order_once(self, mock_status):
        booking_key = self._create_checkout()
        prepared = self._prepare(booking_key)
        attempt = CheckoutPaymentAttempt.objects.get(
            attempt_reference=prepared.data['data']['attempt_reference']
        )
        mock_status.return_value = self._details(attempt)

        payload = {
            'attempt_reference': attempt.attempt_reference,
            'invoice_id': '900001',
        }
        first = self.client.post('/api/orders/checkout/myfatoorah/confirm/', payload, format='json')
        second = self.client.post('/api/orders/checkout/myfatoorah/confirm/', payload, format='json')

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(Order.objects.count(), 1)
        order = Order.objects.get()
        self.assertEqual(order.payment_status, 'paid')
        self.assertEqual(order.payment_reference, '0707900001001')
        attempt.refresh_from_db()
        self.assertEqual(attempt.status, 'succeeded')

    @patch('apps.orders.myfatoorah_views.get_payment_status')
    def test_confirm_rejects_amount_mismatch(self, mock_status):
        booking_key = self._create_checkout()
        prepared = self._prepare(booking_key)
        attempt = CheckoutPaymentAttempt.objects.get(
            attempt_reference=prepared.data['data']['attempt_reference']
        )
        mock_status.return_value = self._details(attempt, invoice_value=Decimal('1.00'))

        response = self.client.post(
            '/api/orders/checkout/myfatoorah/confirm/',
            {'attempt_reference': attempt.attempt_reference, 'invoice_id': '900001'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Order.objects.count(), 0)
        attempt.refresh_from_db()
        self.assertEqual(attempt.status, 'failed')

    @patch('apps.orders.myfatoorah_views.get_payment_status')
    def test_confirm_rejects_invoice_without_attempt_reference(self, mock_status):
        booking_key = self._create_checkout()
        prepared = self._prepare(booking_key)
        attempt = CheckoutPaymentAttempt.objects.get(
            attempt_reference=prepared.data['data']['attempt_reference']
        )
        mock_status.return_value = self._details(
            attempt,
            customer_reference='another-reference',
            user_defined_field='',
        )

        response = self.client.post(
            '/api/orders/checkout/myfatoorah/confirm/',
            {'attempt_reference': attempt.attempt_reference, 'invoice_id': '900001'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Order.objects.count(), 0)

    @patch('apps.orders.myfatoorah_views.get_payment_status')
    def test_confirm_keeps_incomplete_invoice_pending(self, mock_status):
        booking_key = self._create_checkout()
        prepared = self._prepare(booking_key)
        attempt = CheckoutPaymentAttempt.objects.get(
            attempt_reference=prepared.data['data']['attempt_reference']
        )
        mock_status.return_value = self._details(
            attempt,
            invoice_status='PENDING',
            transaction_status='INPROGRESS',
            payment_id='',
        )

        response = self.client.post(
            '/api/orders/checkout/myfatoorah/confirm/',
            {'attempt_reference': attempt.attempt_reference, 'invoice_id': '900001'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(Order.objects.count(), 0)
        attempt.refresh_from_db()
        self.assertEqual(attempt.status, 'pending')

    @patch('apps.orders.myfatoorah_views.get_payment_status')
    def test_signed_webhook_can_complete_payment_before_flutter_confirm(self, mock_status):
        booking_key = self._create_checkout()
        prepared = self._prepare(booking_key)
        attempt = CheckoutPaymentAttempt.objects.get(
            attempt_reference=prepared.data['data']['attempt_reference']
        )
        mock_status.return_value = self._details(attempt)
        payload = {
            'Event': {
                'Name': 'PAYMENT_STATUS_CHANGED',
                'Reference': 'WH-900001',
            },
            'Data': {
                'Invoice': {
                    'Id': '900001',
                    'Status': 'PAID',
                    'ExternalIdentifier': '',
                    'UserDefinedField': attempt.attempt_reference,
                },
                'Transaction': {
                    'Status': 'SUCCESS',
                    'PaymentId': '0707900001001',
                },
            },
        }
        canonical = (
            'Invoice.Id=900001,Invoice.Status=PAID,Transaction.Status=SUCCESS,'
            'Transaction.PaymentId=0707900001001,Invoice.ExternalIdentifier='
        )
        signature = base64.b64encode(
            hmac.new(b'test-webhook-secret', canonical.encode(), hashlib.sha256).digest()
        ).decode()

        first = self.client.post(
            '/api/orders/checkout/myfatoorah/webhook/',
            payload,
            format='json',
            HTTP_MYFATOORAH_SIGNATURE=signature,
        )
        second = self.client.post(
            '/api/orders/checkout/myfatoorah/webhook/',
            payload,
            format='json',
            HTTP_MYFATOORAH_SIGNATURE=signature,
        )

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(MyFatoorahWebhookEvent.objects.count(), 1)

    def test_webhook_rejects_invalid_signature(self):
        response = self.client.post(
            '/api/orders/checkout/myfatoorah/webhook/',
            {
                'Event': {
                    'Name': 'PAYMENT_STATUS_CHANGED',
                    'Reference': 'WH-invalid',
                },
                'Data': {
                    'Invoice': {'Id': '1', 'Status': 'PAID'},
                    'Transaction': {'Status': 'SUCCESS', 'PaymentId': '2'},
                },
            },
            format='json',
            HTTP_MYFATOORAH_SIGNATURE='invalid',
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(MyFatoorahWebhookEvent.objects.count(), 0)

    @patch('apps.orders.myfatoorah_views.get_payment_status')
    def test_remaining_balance_payment_uses_verified_amount(self, mock_status):
        booking_key = self._create_checkout()
        cod_response = self.client.post(
            '/api/orders/checkout/create-order/',
            {'bookingUniqueKey': booking_key, 'payment_method': 'cod'},
            format='json',
        )
        self.assertEqual(cod_response.status_code, status.HTTP_201_CREATED)
        order = Order.objects.get()

        prepared = self.client.post(
            f'/api/orders/{order.id}/pay-remaining/myfatoorah/prepare/',
            {'idempotency_key': 'remaining-idem-1'},
            format='json',
        )
        self.assertEqual(prepared.status_code, status.HTTP_201_CREATED)
        attempt = CheckoutPaymentAttempt.objects.get(
            attempt_reference=prepared.data['data']['attempt_reference']
        )
        mock_status.return_value = self._details(
            attempt,
            invoice_id='900002',
            payment_id='0707900002002',
        )

        confirmed = self.client.post(
            f'/api/orders/{order.id}/pay-remaining/myfatoorah/confirm/',
            {'attempt_reference': attempt.attempt_reference, 'invoice_id': '900002'},
            format='json',
        )

        self.assertEqual(confirmed.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        self.assertEqual(order.payment_status, 'paid')
        self.assertEqual(order.remaining_amount, Decimal('0.00'))
