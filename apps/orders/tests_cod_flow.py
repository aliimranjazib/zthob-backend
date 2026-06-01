from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.customers.models import Address
from apps.orders.models import Order, OrderItem, OrderPayment
from apps.riders.models import RiderProfile, RiderProfileReview
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
class CODOrderFlowTest(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(
            username='cod_customer',
            email='cod_customer@example.com',
            password='testpass123',
            role='USER',
        )
        self.tailor = User.objects.create_user(
            username='cod_tailor',
            email='cod_tailor@example.com',
            password='testpass123',
            role='TAILOR',
        )
        self.rider = User.objects.create_user(
            username='cod_rider',
            email='cod_rider@example.com',
            password='testpass123',
            role='RIDER',
        )
        self.other_rider = User.objects.create_user(
            username='cod_other_rider',
            email='cod_other_rider@example.com',
            password='testpass123',
            role='RIDER',
        )
        self.other_customer = User.objects.create_user(
            username='cod_other_customer',
            email='cod_other_customer@example.com',
            password='testpass123',
            role='USER',
        )

        self.tailor_profile, _ = TailorProfile.objects.get_or_create(
            user=self.tailor,
            defaults={'shop_name': 'COD Tailor', 'shop_status': True},
        )
        for rider in [self.rider, self.other_rider]:
            rider_profile, _ = RiderProfile.objects.get_or_create(
                user=rider,
                defaults={'full_name': rider.username, 'phone_number': '+966500000000'},
            )
            RiderProfileReview.objects.get_or_create(
                profile=rider_profile,
                defaults={'review_status': 'approved'},
            )

        self.category = FabricCategory.objects.create(name='Fabric', slug='fabric')
        self.fabric = Fabric.objects.create(
            tailor=self.tailor_profile,
            category=self.category,
            name='COD Fabric',
            price=Decimal('100.00'),
            stock=10,
            is_active=True,
        )
        self.address = Address.objects.create(
            user=self.customer,
            street='123 COD St',
            city='Riyadh',
            country='Saudi Arabia',
        )

        self.customer_client = APIClient()
        self.customer_client.force_authenticate(user=self.customer)
        self.tailor_client = APIClient()
        self.tailor_client.force_authenticate(user=self.tailor)
        self.rider_client = APIClient()
        self.rider_client.force_authenticate(user=self.rider)
        self.other_rider_client = APIClient()
        self.other_rider_client.force_authenticate(user=self.other_rider)
        self.other_customer_client = APIClient()
        self.other_customer_client.force_authenticate(user=self.other_customer)

    def _create_order(self, **overrides):
        defaults = {
            'customer': self.customer,
            'tailor': self.tailor,
            'order_type': 'fabric_only',
            'service_mode': 'home_delivery',
            'payment_method': 'cod',
            'payment_status': 'pending',
            'status': 'confirmed',
            'tailor_status': 'accepted',
            'delivery_address': self.address,
            'subtotal': Decimal('100.00'),
            'tax_amount': Decimal('15.00'),
            'delivery_fee': Decimal('20.00'),
            'total_amount': Decimal('135.00'),
        }
        defaults.update(overrides)
        if 'paid_amount' not in defaults and 'remaining_amount' not in defaults:
            if defaults.get('payment_status') == 'paid':
                defaults['paid_amount'] = defaults['total_amount']
                defaults['remaining_amount'] = Decimal('0.00')
            else:
                defaults['paid_amount'] = Decimal('0.00')
                defaults['remaining_amount'] = defaults['total_amount']
        order = Order.objects.create(**defaults)
        OrderItem.objects.create(
            order=order,
            fabric=self.fabric,
            quantity=1,
            unit_price=Decimal('100.00'),
            total_price=Decimal('100.00'),
        )
        return order

    def test_customer_can_create_cod_order_with_pending_payment(self):
        response = self.customer_client.post(
            '/api/orders/create/',
            data={
                'tailor': self.tailor.id,
                'order_type': 'fabric_only',
                'service_mode': 'home_delivery',
                'payment_method': 'cod',
                'delivery_address': self.address.id,
                'items': [
                    {'fabric': self.fabric.id, 'quantity': 1, 'measurements': {}}
                ],
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['data']['payment_method'], 'cod')
        self.assertEqual(response.data['data']['payment_status'], 'pending')

    def test_cod_pending_is_processable_but_credit_pending_is_not(self):
        cod_order = self._create_order(payment_method='cod', payment_status='pending')
        self._create_order(payment_method='credit_card', payment_status='pending')

        response = self.tailor_client.get('/api/orders/tailor/paid-orders/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order_ids = [order['id'] for order in response.data['data']]
        self.assertIn(cod_order.id, order_ids)
        self.assertEqual(len(order_ids), 1)

    def test_customer_can_pay_remaining_balance_online(self):
        order = self._create_order(
            payment_method='credit_card',
            payment_status='partially_paid',
            payment_plan='partial',
            payment_option='advance_50',
            deposit_amount=Decimal('67.50'),
            paid_amount=Decimal('67.50'),
            remaining_amount=Decimal('67.50'),
        )

        response = self.customer_client.post(
            f'/api/orders/{order.id}/pay-remaining/',
            data={
                'payment_method': 'credit_card',
                'payment_reference': 'txn_remaining_online_001',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        self.assertEqual(order.payment_status, 'paid')
        self.assertEqual(order.paid_amount, order.total_amount)
        self.assertEqual(order.remaining_amount, Decimal('0.00'))
        self.assertEqual(
            OrderPayment.objects.filter(
                order=order,
                payment_type='remaining_balance',
                payment_reference='txn_remaining_online_001',
            ).count(),
            1,
        )

    def test_other_customer_cannot_pay_remaining_balance(self):
        order = self._create_order(
            payment_status='partially_paid',
            paid_amount=Decimal('50.00'),
            remaining_amount=Decimal('85.00'),
        )

        response = self.other_customer_client.post(
            f'/api/orders/{order.id}/pay-remaining/',
            data={
                'payment_method': 'credit_card',
                'payment_reference': 'txn_wrong_customer',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_pay_remaining_rejects_duplicate_payment_reference(self):
        first_order = self._create_order(
            payment_status='partially_paid',
            paid_amount=Decimal('50.00'),
            remaining_amount=Decimal('85.00'),
        )
        second_order = self._create_order(
            payment_status='partially_paid',
            paid_amount=Decimal('50.00'),
            remaining_amount=Decimal('85.00'),
        )
        OrderPayment.objects.create(
            order=first_order,
            amount=Decimal('85.00'),
            payment_method='credit_card',
            payment_type='remaining_balance',
            payment_reference='txn_duplicate_remaining',
            collected_by=self.customer,
        )

        response = self.customer_client.post(
            f'/api/orders/{second_order.id}/pay-remaining/',
            data={
                'payment_method': 'credit_card',
                'payment_reference': 'txn_duplicate_remaining',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_pay_remaining_rejects_fully_paid_order(self):
        order = self._create_order(
            payment_status='paid',
            paid_amount=Decimal('135.00'),
            remaining_amount=Decimal('0.00'),
        )

        response = self.customer_client.post(
            f'/api/orders/{order.id}/pay-remaining/',
            data={
                'payment_method': 'credit_card',
                'payment_reference': 'txn_no_balance',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cod_pending_order_is_available_to_rider(self):
        order = self._create_order(
            payment_method='cod',
            payment_status='pending',
            rider=None,
            rider_status='none',
        )

        response = self.rider_client.get('/api/riders/orders/available/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order_ids = [item['id'] for item in response.data['data']]
        self.assertIn(order.id, order_ids)

    def test_credit_card_pending_cannot_be_accepted_by_action(self):
        order = self._create_order(
            payment_method='credit_card',
            payment_status='pending',
            tailor_status='none',
        )

        response = self.tailor_client.post(
            f'/api/orders/{order.id}/action/',
            data={'action': 'accept_order', 'role': 'TAILOR', 'data': {}},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        order.refresh_from_db()
        self.assertEqual(order.tailor_status, 'none')

    def test_assigned_rider_can_collect_cash_payment(self):
        order = self._create_order(
            rider=self.rider,
            rider_status='on_way_to_delivery',
            status='ready_for_delivery',
        )

        response = self.rider_client.post(
            f'/api/orders/{order.id}/action/',
            data={'action': 'collect_cash_payment', 'role': 'RIDER', 'data': {}},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        self.assertEqual(order.payment_status, 'paid')
        self.assertEqual(order.remaining_amount, Decimal('0.00'))
        self.assertEqual(order.paid_amount, order.total_amount)
        self.assertEqual(OrderPayment.objects.filter(order=order, payment_type='full_payment').count(), 1)
        self.assertEqual(response.data['data']['payment_method'], 'cod')
        self.assertEqual(response.data['data']['payment_status'], 'paid')
        action_keys = [action['key'] for action in response.data['data']['available_actions']]
        self.assertNotIn('collect_cash_payment', action_keys)

    def test_unassigned_rider_cannot_collect_cash_payment(self):
        order = self._create_order(
            rider=self.rider,
            rider_status='on_way_to_delivery',
            status='ready_for_delivery',
        )

        response = self.other_rider_client.post(
            f'/api/orders/{order.id}/action/',
            data={'action': 'collect_cash_payment', 'role': 'RIDER', 'data': {}},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        order.refresh_from_db()
        self.assertEqual(order.payment_status, 'pending')

    def test_walk_in_tailor_can_collect_cash_payment(self):
        order = self._create_order(
            service_mode='walk_in',
            payment_method='cod',
            payment_status='pending',
            status='ready_for_pickup',
            rider=None,
        )

        response = self.tailor_client.post(
            f'/api/orders/{order.id}/action/',
            data={'action': 'collect_cash_payment', 'role': 'TAILOR', 'data': {}},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        self.assertEqual(order.payment_status, 'paid')

    def test_partially_paid_order_must_collect_balance_before_delivery(self):
        order = self._create_order(
            payment_method='credit_card',
            payment_status='partially_paid',
            payment_plan='partial',
            payment_option='advance_50',
            deposit_amount=Decimal('67.50'),
            paid_amount=Decimal('67.50'),
            remaining_amount=Decimal('67.50'),
            rider=self.rider,
            rider_status='on_way_to_delivery',
            status='ready_for_delivery',
        )

        response = self.rider_client.post(
            f'/api/orders/{order.id}/action/',
            data={'action': 'mark_delivered', 'role': 'RIDER', 'data': {}},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.rider_client.post(
            f'/api/orders/{order.id}/action/',
            data={'action': 'collect_cash_payment', 'role': 'RIDER', 'data': {}},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        self.assertEqual(order.payment_status, 'paid')
        self.assertEqual(order.remaining_amount, Decimal('0.00'))
        self.assertEqual(OrderPayment.objects.filter(order=order, payment_type='remaining_balance').count(), 1)

        response = self.rider_client.post(
            f'/api/orders/{order.id}/action/',
            data={'action': 'mark_delivered', 'role': 'RIDER', 'data': {}},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
