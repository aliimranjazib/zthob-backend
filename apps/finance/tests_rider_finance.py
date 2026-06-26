from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.finance.models import (
    PayoutRequest,
    RiderPayoutRequest,
    RiderWallet,
    RiderWalletTransaction,
    TailorWallet,
)
from apps.finance.services import WalletService
from apps.orders.models import Order


User = get_user_model()


@override_settings(
    SECURE_SSL_REDIRECT=False,
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }
)
class RiderFinanceAPITest(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(
            username='finance_customer',
            password='testpass123',
            role='USER',
        )
        self.tailor = User.objects.create_user(
            username='finance_tailor',
            password='testpass123',
            role='TAILOR',
        )
        self.rider = User.objects.create_user(
            username='finance_rider',
            password='testpass123',
            role='RIDER',
        )
        self.measurement_rider = User.objects.create_user(
            username='finance_measurement_rider',
            password='testpass123',
            role='RIDER',
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.rider)

    def _completed_delivery_order(self, **overrides):
        defaults = {
            'customer': self.customer,
            'tailor': self.tailor,
            'rider': self.rider,
            'assigned_rider': self.rider,
            'delivery_rider': self.rider,
            'service_mode': 'home_delivery',
            'status': 'delivered',
            'payment_status': 'paid',
            'subtotal': Decimal('100.00'),
            'stitching_price': Decimal('20.00'),
            'delivery_fee': Decimal('25.00'),
            'system_fee': Decimal('3.00'),
            'total_amount': Decimal('148.00'),
        }
        defaults.update(overrides)
        return Order.objects.create(**defaults)

    def test_completed_delivery_credits_rider_wallet_once(self):
        order = self._completed_delivery_order()

        wallet = RiderWallet.objects.get(rider=self.rider)
        self.assertEqual(wallet.available_balance, Decimal('25.00'))
        self.assertEqual(wallet.total_earned, Decimal('25.00'))
        self.assertEqual(RiderWalletTransaction.objects.filter(order=order).count(), 1)

        WalletService.process_rider_order_earning(order)
        wallet.refresh_from_db()
        self.assertEqual(wallet.available_balance, Decimal('25.00'))
        self.assertEqual(RiderWalletTransaction.objects.filter(order=order).count(), 1)

    def test_measurement_and_delivery_earnings_are_separate_for_different_riders(self):
        order = self._completed_delivery_order(
            measurement_rider=self.measurement_rider,
            status='in_progress',
            rider_status='accepted',
            delivery_fee=Decimal('20.00'),
            measurement_fee=Decimal('15.00'),
            total_amount=Decimal('138.00'),
        )
        order.rider_status = 'measurement_taken'
        order.save(update_fields=['rider_status', 'updated_at'])
        WalletService.process_measurement_rider_order_earning(order)
        order.status = 'delivered'
        order.save(update_fields=['status', 'updated_at'])

        delivery_wallet = RiderWallet.objects.get(rider=self.rider)
        measurement_wallet = RiderWallet.objects.get(rider=self.measurement_rider)
        self.assertEqual(delivery_wallet.available_balance, Decimal('20.00'))
        self.assertEqual(measurement_wallet.available_balance, Decimal('15.00'))
        self.assertEqual(
            RiderWalletTransaction.objects.filter(order=order, earning_type='delivery').count(),
            1,
        )
        self.assertEqual(
            RiderWalletTransaction.objects.filter(order=order, earning_type='measurement').count(),
            1,
        )

        WalletService.process_rider_order_earning(order)
        WalletService.process_measurement_rider_order_earning(order)
        self.assertEqual(RiderWalletTransaction.objects.filter(order=order).count(), 2)

    def test_same_rider_can_receive_measurement_and_delivery_earnings(self):
        order = self._completed_delivery_order(
            measurement_rider=self.rider,
            status='in_progress',
            rider_status='accepted',
            delivery_fee=Decimal('20.00'),
            measurement_fee=Decimal('15.00'),
            total_amount=Decimal('138.00'),
        )
        order.rider_status = 'measurement_taken'
        order.save(update_fields=['rider_status', 'updated_at'])
        WalletService.process_measurement_rider_order_earning(order)
        order.status = 'delivered'
        order.save(update_fields=['status', 'updated_at'])

        wallet = RiderWallet.objects.get(rider=self.rider)
        self.assertEqual(wallet.available_balance, Decimal('35.00'))
        self.assertEqual(wallet.total_earned, Decimal('35.00'))
        self.assertEqual(
            set(RiderWalletTransaction.objects.filter(order=order).values_list('earning_type', flat=True)),
            {'delivery', 'measurement'},
        )

    def test_rider_wallet_endpoint_returns_rider_balance(self):
        self._completed_delivery_order(delivery_fee=Decimal('30.00'))

        response = self.client.get('/api/finance/wallet/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['available_balance'], '30.00')
        self.assertEqual(response.data['total_earned'], '30.00')

    def test_rider_transaction_history_endpoint_returns_rider_transactions(self):
        order = self._completed_delivery_order(delivery_fee=Decimal('18.00'))

        response = self.client.get('/api/finance/transactions/')

        self.assertEqual(response.status_code, 200)
        results = response.data['results'] if isinstance(response.data, dict) and 'results' in response.data else response.data
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['amount'], '18.00')
        self.assertEqual(results[0]['earning_type'], 'delivery')
        self.assertEqual(results[0]['order']['id'], order.id)

    def test_rider_can_request_payout_from_available_balance(self):
        self._completed_delivery_order(delivery_fee=Decimal('40.00'))

        response = self.client.post(
            '/api/finance/payouts/',
            data={
                'amount': '25.00',
                'bank_name': 'Al Rajhi Bank',
                'account_number': '123456789',
                'iban': 'SA0000000000000000000000',
                'account_holder_name': 'Finance Rider',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        payout = RiderPayoutRequest.objects.get(rider=self.rider)
        self.assertEqual(payout.amount, Decimal('25.00'))
        self.assertEqual(payout.status, 'pending')

    def test_rider_payout_rejects_insufficient_balance(self):
        self._completed_delivery_order(delivery_fee=Decimal('10.00'))

        response = self.client.post(
            '/api/finance/payouts/',
            data={
                'amount': '25.00',
                'bank_name': 'Al Rajhi Bank',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(RiderPayoutRequest.objects.filter(rider=self.rider).exists())

    def test_tailor_finance_endpoint_still_uses_tailor_wallet(self):
        TailorWallet.objects.create(
            tailor=self.tailor,
            available_balance=Decimal('75.00'),
            total_earned=Decimal('75.00'),
        )
        self.client.force_authenticate(user=self.tailor)

        wallet_response = self.client.get('/api/finance/wallet/')
        payout_response = self.client.post(
            '/api/finance/payouts/',
            data={
                'amount': '50.00',
                'bank_name': 'Al Rajhi Bank',
                'account_holder_name': 'Finance Tailor',
            },
            format='json',
        )

        self.assertEqual(wallet_response.status_code, 200)
        self.assertEqual(wallet_response.data['available_balance'], '75.00')
        self.assertEqual(payout_response.status_code, 201)
        self.assertTrue(PayoutRequest.objects.filter(tailor=self.tailor, amount=Decimal('50.00')).exists())
