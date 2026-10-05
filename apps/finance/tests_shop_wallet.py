"""Per-shop wallet scoping for multi-shop owners."""

from decimal import Decimal

from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import CustomUser
from apps.core.services import PhoneVerificationService
from apps.finance.models import TailorWallet
from apps.finance.services import WalletService
from apps.orders.models import Order

TEST_REST_FRAMEWORK = {
    **settings.REST_FRAMEWORK,
    'DEFAULT_THROTTLE_CLASSES': [],
}


@override_settings(REST_FRAMEWORK=TEST_REST_FRAMEWORK)
class MultiShopWalletTestCase(TestCase):
    def setUp(self):
        from apps.accounts import views as account_views

        account_views.PhoneLoginView.throttle_classes = []
        account_views.PhoneVerifyView.throttle_classes = []

        self.client = APIClient()
        self.phone_login_url = reverse('accounts:phone-login')
        self.phone_verify_url = reverse('accounts:phone-verify')
        self.owner_switch_url = reverse('accounts:owner-switch-shop')
        self.shops_url = reverse('owner-shops')
        self.wallet_url = reverse('tailor-wallet')
        self.test_otp = PhoneVerificationService.TEST_OTP
        self.owner_phone = '0500000101'

        self.customer = CustomUser.objects.create_user(
            username='wallet_shop_customer',
            phone='0500000102',
            role='USER',
        )

    def _login_owner(self):
        self.client.post(self.phone_login_url, {'phone': self.owner_phone})
        response = self.client.post(self.phone_verify_url, {
            'phone': self.owner_phone,
            'otp_code': self.test_otp,
            'name': 'Wallet Owner',
            'role': 'TAILOR',
            'app_entry': 'owner',
        })
        token = response.data['data']['tokens']['access_token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        return response

    def _create_shop(self, name):
        response = self.client.post(
            self.shops_url,
            {'shop_name': name, 'address': 'Riyadh'},
            format='json',
        )
        return response.data['data']

    def _switch_shop(self, shop_id):
        response = self.client.post(
            self.owner_switch_url,
            {'shop_id': shop_id},
            format='json',
        )
        token = response.data['data']['tokens']['access_token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def _credit_order(self, owner, shop_id, order_number, amount):
        order = Order.objects.create(
            customer=self.customer,
            tailor=owner,
            shop_id=shop_id,
            order_number=order_number,
            service_mode='home_delivery',
            status='delivered',
            payment_status='paid',
            subtotal=amount,
            stitching_price=Decimal('0.00'),
            express_fee=Decimal('0.00'),
            system_fee=Decimal('0.00'),
            total_amount=amount,
        )
        WalletService.process_order_earning(order)
        return order

    def test_wallet_balance_scoped_to_active_shop(self):
        self._login_owner()
        owner = CustomUser.objects.get(phone=self.owner_phone)
        shop_a = self._create_shop('Wallet Shop A')
        shop_b = self._create_shop('Wallet Shop B')

        self._credit_order(owner, shop_a['id'], 'W-SHOP-A', Decimal('40.00'))
        self._credit_order(owner, shop_b['id'], 'W-SHOP-B', Decimal('90.00'))

        self._switch_shop(shop_a['id'])
        response_a = self.client.get(self.wallet_url)
        self.assertEqual(response_a.status_code, status.HTTP_200_OK)
        self.assertEqual(response_a.data['available_balance'], '40.00')
        self.assertEqual(response_a.data['shop_id'], shop_a['id'])

        self._switch_shop(shop_b['id'])
        response_b = self.client.get(self.wallet_url)
        self.assertEqual(response_b.status_code, status.HTTP_200_OK)
        self.assertEqual(response_b.data['available_balance'], '90.00')
        self.assertEqual(response_b.data['shop_id'], shop_b['id'])

        self.assertEqual(
            TailorWallet.objects.filter(tailor=owner).count(),
            2,
        )

    def test_multi_shop_owner_without_session_gets_400(self):
        self._login_owner()
        owner = CustomUser.objects.get(phone=self.owner_phone)
        self._create_shop('Wallet Shop X')
        self._create_shop('Wallet Shop Y')

        self.client.credentials()
        self.client.force_authenticate(user=owner)

        response = self.client.get(self.wallet_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
