"""Customer order list/detail show Order.shop tailor info (multi-shop)."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.customers.models import Address
from apps.orders.models import Order
from apps.orders.serializers import OrderListSerializer, OrderSerializer
from apps.tailors.models import TailorProfile, TailorProfileReview

User = get_user_model()


@override_settings(SECURE_SSL_REDIRECT=False)
class CustomerOrderShopInfoTest(APITestCase):
    def setUp(self):
        self.customer = User.objects.create_user(
            username='cust_order_shop',
            password='testpass123',
            role='USER',
        )
        self.owner = User.objects.create_user(
            username='owner_order_shop',
            password='testpass123',
            role='TAILOR',
        )
        self.primary = self.owner.tailor_profile
        self.primary.shop_name = 'Primary Shop'
        self.primary.save()

        self.branch = TailorProfile.objects.create(
            owner=self.owner,
            user=None,
            shop_name='Branch Shop',
            shop_status=True,
            address='Branch pickup address',
            contact_number='0503333444',
        )
        TailorProfileReview.objects.create(profile=self.branch, review_status='approved')

        self.order = Order.objects.create(
            customer=self.customer,
            tailor=self.owner,
            shop=self.branch,
            order_type='fabric_with_stitching',
            service_mode='home_delivery',
            status='confirmed',
            payment_method='cod',
            payment_status='pending',
            total_amount=Decimal('100.00'),
            paid_amount=Decimal('0.00'),
            remaining_amount=Decimal('100.00'),
        )
        Address.objects.create(
            user=self.owner,
            street='HQ',
            city='Riyadh',
            country='Saudi Arabia',
            address='Owner default',
            is_default=True,
        )
        self.client.force_authenticate(user=self.customer)

    def test_list_serializer_uses_branch_shop_name(self):
        data = OrderListSerializer(self.order).data
        self.assertEqual(data['tailor_name'], 'Branch Shop')

    def test_detail_serializer_tailor_info(self):
        data = OrderSerializer(self.order).data
        self.assertEqual(data['tailor_name'], 'Branch Shop')
        self.assertEqual(data['tailor_info']['shop_name'], 'Branch Shop')
        self.assertEqual(data['tailor_info']['address']['address'], 'Branch pickup address')

    def test_my_orders_api(self):
        response = self.client.get('/api/orders/customer/my-orders/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data'][0]['tailor_name'], 'Branch Shop')

    def test_order_detail_api(self):
        response = self.client.get(f'/api/orders/{self.order.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['tailor_name'], 'Branch Shop')
        self.assertEqual(response.data['data']['tailor_info']['shop_name'], 'Branch Shop')

    def test_legacy_order_without_shop_uses_primary_profile(self):
        legacy = Order.objects.create(
            customer=self.customer,
            tailor=self.owner,
            shop=None,
            order_type='fabric_only',
            service_mode='home_delivery',
            status='confirmed',
            payment_method='cod',
            payment_status='pending',
            total_amount=Decimal('50.00'),
            paid_amount=Decimal('0.00'),
            remaining_amount=Decimal('50.00'),
        )
        data = OrderListSerializer(legacy).data
        self.assertEqual(data['tailor_name'], 'Primary Shop')
