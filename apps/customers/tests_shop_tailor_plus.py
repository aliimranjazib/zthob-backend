"""Customer-facing Tailor Plus behavior."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.customers.models import CustomerProfile
from apps.orders.models import Order, OrderItem
from apps.tailors.models import ShopTailorPlusSubscription, TailorProfile, TailorProfileReview

User = get_user_model()

WALK_IN_MEASUREMENTS = {'length': 140, 'shoulder': 46, 'unit': 'cm'}


@override_settings(SECURE_SSL_REDIRECT=False)
class CustomerPlusMeasurementsTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = User.objects.create_user(
            username='plus_customer',
            password='pass',
            role='USER',
        )
        CustomerProfile.objects.get_or_create(user=self.customer)
        self.tailor = User.objects.create_user(
            username='plus_tailor',
            password='pass',
            role='TAILOR',
        )
        self.shop = TailorProfile.objects.create(
            owner=self.tailor,
            user=self.tailor,
            shop_name='Plus Walk-in Shop',
            shop_status=True,
        )
        TailorProfileReview.objects.update_or_create(
            profile=self.shop,
            defaults={'review_status': 'approved'},
        )
        self.client.force_authenticate(user=self.customer)

    def _walk_in_order(self):
        taken_at = timezone.now()
        order = Order.objects.create(
            customer=self.customer,
            tailor=self.tailor,
            shop=self.shop,
            order_type='fabric_with_stitching',
            service_mode='walk_in',
            status='collected',
            tailor_status='stitched',
            rider_status='none',
            payment_status='paid',
            total_amount=Decimal('100.00'),
            paid_amount=Decimal('100.00'),
            remaining_amount=Decimal('0.00'),
            measurement_taken_at=taken_at,
        )
        OrderItem.objects.create(
            order=order,
            quantity=1,
            unit_price=Decimal('100.00'),
            total_price=Decimal('100.00'),
            measurements=WALK_IN_MEASUREMENTS,
        )
        return order

    def test_walk_in_hidden_from_library_when_shop_is_plus(self):
        self._walk_in_order()
        ShopTailorPlusSubscription.objects.create(
            shop=self.shop,
            status=ShopTailorPlusSubscription.STATUS_ACTIVE,
        )

        response = self.client.get('/api/customers/measurements/')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        recipient = response.data['data']['recipients'][0]
        self.assertEqual(recipient['order_history'], [])

    def test_walk_in_visible_in_library_when_shop_not_plus(self):
        self._walk_in_order()

        response = self.client.get('/api/customers/measurements/')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        recipient = response.data['data']['recipients'][0]
        self.assertEqual(len(recipient['order_history']), 1)

    def test_reusable_measurements_endpoint_for_plus_shop(self):
        order = self._walk_in_order()
        ShopTailorPlusSubscription.objects.create(
            shop=self.shop,
            status=ShopTailorPlusSubscription.STATUS_ACTIVE,
        )

        response = self.client.get(
            f'/api/customers/tailors/{self.shop.id}/reusable-measurements/'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        customer_payload = response.data['data']['customer']
        self.assertIsNotNone(customer_payload)
        self.assertEqual(customer_payload['source_order_id'], order.id)
        self.assertEqual(customer_payload['measurements']['length'], 140)

    def test_tailor_detail_includes_is_tailor_plus(self):
        ShopTailorPlusSubscription.objects.create(
            shop=self.shop,
            status=ShopTailorPlusSubscription.STATUS_ACTIVE,
        )
        response = self.client.get(f'/api/customers/tailors/{self.shop.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertTrue(response.data['data']['is_tailor_plus'])
