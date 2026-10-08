"""Checkout accepts shop profile id in ``tailor`` (multi-shop customer apps)."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.customers.models import Address
from apps.orders.models import Order
from apps.tailors.models import Fabric, FabricCategory, TailorProfile, TailorProfileReview

User = get_user_model()


@override_settings(
    SECURE_SSL_REDIRECT=False,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}},
)
class CheckoutMultiShopTailorIdTest(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(
            username='ms_checkout_customer',
            password='testpass123',
            role='USER',
        )
        self.owner = User.objects.create_user(
            username='ms_checkout_owner',
            password='testpass123',
            role='TAILOR',
        )
        self.primary = self.owner.tailor_profile
        self.primary.shop_name = 'Primary Shop'
        self.primary.shop_status = True
        self.primary.save()
        TailorProfileReview.objects.update_or_create(
            profile=self.primary,
            defaults={'review_status': 'approved'},
        )

        self.branch = TailorProfile.objects.create(
            owner=self.owner,
            user=None,
            shop_name='Branch Shop',
            shop_status=True,
        )
        TailorProfileReview.objects.create(profile=self.branch, review_status='approved')

        category = FabricCategory.objects.create(name='MS Fabric', slug='ms-fabric')
        self.fabric = Fabric.objects.create(
            tailor=self.branch,
            category=category,
            name='Branch Fabric',
            price=Decimal('120.00'),
            stock=5,
            is_active=True,
            approval_status='approved',
        )
        self.address = Address.objects.create(
            user=self.customer,
            street='Branch St',
            city='Riyadh',
            country='Saudi Arabia',
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.customer)

    def _payload_with_tailor_as_shop_id(self):
        return {
            'tailor': self.branch.id,
            'order_type': 'fabric_with_stitching',
            'service_mode': 'home_delivery',
            'payment_method': 'cod',
            'delivery_address': self.address.id,
            'items': [
                {'fabric': self.fabric.id, 'quantity': 1, 'measurements': {}},
            ],
        }

    def test_checkout_accepts_shop_profile_id_in_tailor_field(self):
        response = self.client.post(
            '/api/orders/checkout/',
            data=self._payload_with_tailor_as_shop_id(),
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertTrue(response.data['success'])

    def test_create_order_sets_shop_on_order(self):
        checkout_resp = self.client.post(
            '/api/orders/checkout/',
            data=self._payload_with_tailor_as_shop_id(),
            format='json',
        )
        self.assertEqual(checkout_resp.status_code, status.HTTP_201_CREATED)
        booking_key = checkout_resp.data['data']['bookingUniqueKey']

        order_resp = self.client.post(
            '/api/orders/checkout/create-order/',
            data={'bookingUniqueKey': booking_key, 'payment_method': 'cod'},
            format='json',
        )
        self.assertEqual(order_resp.status_code, status.HTTP_201_CREATED, order_resp.data)
        order_id = order_resp.data['data']['id']
        order = Order.objects.get(pk=order_id)
        self.assertEqual(order.shop_id, self.branch.id)
        self.assertEqual(order.tailor_id, self.owner.id)
