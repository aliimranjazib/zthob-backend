"""Tests for owner cross-shop orders and reports."""

from decimal import Decimal

from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import CustomUser
from apps.core.services import PhoneVerificationService
from apps.orders.models import Order
from apps.tailors.models import TailorProfile

TEST_REST_FRAMEWORK = {
    **settings.REST_FRAMEWORK,
    'DEFAULT_THROTTLE_CLASSES': [],
}


@override_settings(REST_FRAMEWORK=TEST_REST_FRAMEWORK)
class OwnerOrdersReportsTestCase(TestCase):
    def setUp(self):
        from apps.accounts import views as account_views

        account_views.PhoneLoginView.throttle_classes = []
        account_views.PhoneVerifyView.throttle_classes = []

        self.client = APIClient()
        self.phone_login_url = reverse('accounts:phone-login')
        self.phone_verify_url = reverse('accounts:phone-verify')
        self.owner_switch_url = reverse('accounts:owner-switch-shop')
        self.shops_url = reverse('owner-shops')
        self.orders_url = reverse('owner-orders')
        self.reports_url = reverse('owner-reports')
        self.test_otp = PhoneVerificationService.TEST_OTP
        self.owner_phone = '0500000004'

        self.customer = CustomUser.objects.create_user(
            username='owner_phase4_customer',
            phone='0500000007',
            role='USER',
        )

    def _login_owner(self):
        self.client.post(self.phone_login_url, {'phone': self.owner_phone})
        response = self.client.post(self.phone_verify_url, {
            'phone': self.owner_phone,
            'otp_code': self.test_otp,
            'name': 'Owner User',
            'role': 'TAILOR',
            'app_entry': 'owner',
        })
        token = response.data['data']['tokens']['access_token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        return response

    def _create_shop(self, name, **extra):
        payload = {'shop_name': name, 'address': 'Riyadh', **extra}
        response = self.client.post(self.shops_url, payload, format='json')
        return response.data['data']

    def _create_order(self, owner, shop, order_number, **extra):
        defaults = {
            'customer': self.customer,
            'tailor': owner,
            'shop_id': shop['id'],
            'order_number': order_number,
            'subtotal': Decimal('100.00'),
            'total_amount': Decimal('100.00'),
            'status': 'confirmed',
            'payment_status': 'paid',
            'service_mode': 'walk_in',
        }
        defaults.update(extra)
        return Order.objects.create(**defaults)

    def test_owner_sees_orders_from_all_owned_shops(self):
        self._login_owner()
        owner = CustomUser.objects.get(phone=self.owner_phone)
        shop_a = self._create_shop('Orders Shop A')
        shop_b = self._create_shop('Orders Shop B')

        self._create_order(owner, shop_a, '90001')
        self._create_order(owner, shop_b, '90002')

        response = self.client.get(self.orders_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order_numbers = {row['order_number'] for row in response.data['data']}
        self.assertEqual(order_numbers, {'90001', '90002'})

    def test_owner_can_filter_orders_by_shop(self):
        self._login_owner()
        owner = CustomUser.objects.get(phone=self.owner_phone)
        shop_a = self._create_shop('Filter Shop A')
        shop_b = self._create_shop('Filter Shop B')

        self._create_order(owner, shop_a, '90003')
        self._create_order(owner, shop_b, '90004')

        response = self.client.get(self.orders_url, {'shop_id': shop_a['id']})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['data']), 1)
        self.assertEqual(response.data['data'][0]['order_number'], '90003')

    def test_order_detail_includes_shop_info(self):
        self._login_owner()
        owner = CustomUser.objects.get(phone=self.owner_phone)
        shop = self._create_shop(
            'Detail Shop',
            contact_number='0512345678',
            working_hours={'monday': {'is_open': True, 'start_time': '09:00', 'end_time': '18:00'}},
        )
        order = self._create_order(owner, shop, '90010')

        detail_url = reverse('owner-order-detail', kwargs={'order_id': order.id})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.data['data']
        self.assertEqual(payload['shop_id'], shop['id'])
        self.assertEqual(payload['shop_info']['shop_name'], 'Detail Shop')
        self.assertEqual(payload['shop_info']['contact_number'], '+966512345678')
        self.assertEqual(payload['tailor_name'], 'Detail Shop')

    def test_shop_session_scopes_tailor_my_orders_endpoint(self):
        self._login_owner()
        owner = CustomUser.objects.get(phone=self.owner_phone)
        shop_a = self._create_shop('Session Shop A')
        shop_b = self._create_shop('Session Shop B')

        self._create_order(owner, shop_a, '90005')
        self._create_order(owner, shop_b, '90006')

        switch = self.client.post(self.owner_switch_url, {'shop_id': shop_a['id']})
        token = switch.data['data']['tokens']['access_token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        response = self.client.get('/api/orders/tailor/my-orders/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order_numbers = {row['order_number'] for row in response.data['data']}
        self.assertEqual(order_numbers, {'90005'})

    def test_owner_reports_respect_period_filter(self):
        self._login_owner()
        owner = CustomUser.objects.get(phone=self.owner_phone)
        shop = self._create_shop('Report Shop A')

        old_order = self._create_order(owner, shop, '90007')
        old_timestamp = timezone.now() - timezone.timedelta(days=40)
        Order.objects.filter(pk=old_order.pk).update(
            created_at=old_timestamp,
            updated_at=old_timestamp,
        )

        recent_order = self._create_order(owner, shop, '90008')
        recent_order.status = 'collected'
        recent_order.save(update_fields=['status'])

        response = self.client.get(self.reports_url, {'period': 'this_month'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        summary = response.data['data']['summary']
        self.assertEqual(summary['orders_total'], 1)
        self.assertEqual(summary['orders_completed'], 1)
        self.assertIn('analytics', summary)
        self.assertEqual(summary['analytics']['combined']['orders_completed'], 1)

    def test_owner_reports_include_home_delivery_and_walk_in(self):
        self._login_owner()
        owner = CustomUser.objects.get(phone=self.owner_phone)
        shop = self._create_shop('Analytics Shop')

        walk_in = self._create_order(owner, shop, '90011', service_mode='walk_in')
        walk_in.status = 'collected'
        walk_in.save(update_fields=['status'])

        home = self._create_order(
            owner,
            shop,
            '90012',
            service_mode='home_delivery',
            total_amount=Decimal('200.00'),
        )
        home.status = 'delivered'
        home.save(update_fields=['status'])

        response = self.client.get(self.reports_url, {'period': 'this_month'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        analytics = response.data['data']['summary']['analytics']
        self.assertEqual(analytics['walk_in']['orders_completed'], 1)
        self.assertEqual(analytics['home_delivery']['orders_completed'], 1)
        self.assertEqual(analytics['combined']['orders_completed'], 2)

    def test_other_owner_cannot_read_foreign_owner_orders(self):
        self._login_owner()
        owner = CustomUser.objects.get(phone=self.owner_phone)
        shop = self._create_shop('Private Orders Shop')
        order = self._create_order(owner, shop, '90009')

        other = CustomUser.objects.create_user(
            username='other_owner_orders',
            phone='0500000005',
            role='TAILOR',
        )
        TailorProfile.objects.filter(owner=other, user=other).update(shop_name='Other Shop')

        detail_url = reverse('owner-order-detail', kwargs={'order_id': order.id})
        self.client.force_authenticate(user=other)
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
