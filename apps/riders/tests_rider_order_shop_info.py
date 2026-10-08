"""Rider order APIs show Order.shop name, not primary tailor_profile only."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.customers.models import Address
from apps.orders.models import Order
from apps.riders.serializers import RiderOrderDetailSerializer, RiderOrderListSerializer
from apps.tailors.models import TailorProfile, TailorProfileReview

User = get_user_model()


@override_settings(SECURE_SSL_REDIRECT=False)
class RiderOrderShopInfoSerializerTest(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username='rider_shop_owner',
            password='testpass123',
            role='TAILOR',
        )
        self.primary = self.owner.tailor_profile
        self.primary.shop_name = 'Primary Shop'
        self.primary.save()

        self.branch = TailorProfile.objects.create(
            owner=self.owner,
            user=None,
            shop_name='Branch Pickup Shop',
            shop_status=True,
            address='Branch street, Riyadh',
            contact_number='0501111222',
        )
        TailorProfileReview.objects.create(profile=self.branch, review_status='approved')

        self.customer = User.objects.create_user(
            username='rider_shop_customer',
            password='testpass123',
            role='USER',
        )
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
            street='Owner HQ',
            city='Riyadh',
            country='Saudi Arabia',
            address='Owner default address',
            is_default=True,
        )

    def test_list_serializer_uses_order_shop_name(self):
        data = RiderOrderListSerializer(self.order).data
        self.assertEqual(data['tailor_name'], 'Branch Pickup Shop')

    def test_detail_serializer_uses_order_shop_name_and_address(self):
        data = RiderOrderDetailSerializer(self.order).data
        info = data['tailor_info']
        self.assertEqual(info['shop_name'], 'Branch Pickup Shop')
        self.assertEqual(info['address']['address'], 'Branch street, Riyadh')
