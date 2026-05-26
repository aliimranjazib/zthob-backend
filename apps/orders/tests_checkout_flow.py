from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.customers.models import Address
from apps.orders.models import CheckoutSession, Order
from apps.tailors.models import Fabric, FabricCategory, TailorProfile


User = get_user_model()


@override_settings(
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
        self.assertEqual(order.payment_reference, 'txn_checkout_001')
        self.assertEqual(checkout.status, 'order_created')
        self.assertEqual(checkout.order, order)

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
