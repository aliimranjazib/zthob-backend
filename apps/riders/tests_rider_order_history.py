from datetime import datetime, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.customers.models import Address
from apps.orders.models import Order, OrderStatusHistory
from apps.riders.models import RiderProfile
from apps.tailors.models import TailorProfile


User = get_user_model()


@override_settings(
    SECURE_SSL_REDIRECT=False,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}},
)
class RiderOrderHistoryViewTest(APITestCase):
    def setUp(self):
        self.customer = User.objects.create_user(
            username='history_customer',
            password='testpass123',
            role='USER',
            first_name='Ali',
            last_name='Ahmed',
        )
        self.tailor = User.objects.create_user(
            username='history_tailor',
            password='testpass123',
            role='TAILOR',
        )
        TailorProfile.objects.get_or_create(
            user=self.tailor,
            defaults={'shop_name': 'History Shop', 'shop_status': True},
        )
        self.rider = User.objects.create_user(
            username='history_rider',
            password='testpass123',
            role='RIDER',
        )
        RiderProfile.objects.get_or_create(
            user=self.rider,
            defaults={'full_name': 'History Rider', 'phone_number': '+966501234567'},
        )
        self.other_rider = User.objects.create_user(
            username='other_rider',
            password='testpass123',
            role='RIDER',
        )
        RiderProfile.objects.get_or_create(
            user=self.other_rider,
            defaults={'full_name': 'Other Rider', 'phone_number': '+966501234568'},
        )
        self.non_rider = User.objects.create_user(
            username='history_user',
            password='testpass123',
            role='USER',
        )
        self.address = Address.objects.create(
            user=self.customer,
            street='123 History St',
            city='Riyadh',
            country='Saudi Arabia',
        )
        self.rider_client = APIClient()
        self.rider_client.force_authenticate(user=self.rider)
        self.non_rider_client = APIClient()
        self.non_rider_client.force_authenticate(user=self.non_rider)

    def _create_order(self, **overrides):
        defaults = {
            'customer': self.customer,
            'tailor': self.tailor,
            'order_type': 'fabric_with_stitching',
            'service_mode': 'home_delivery',
            'payment_method': 'cod',
            'payment_status': 'paid',
            'status': 'in_progress',
            'tailor_status': 'accepted',
            'delivery_address': self.address,
            'subtotal': Decimal('100.00'),
            'tax_amount': Decimal('15.00'),
            'delivery_fee': Decimal('20.00'),
            'total_amount': Decimal('135.00'),
            'paid_amount': Decimal('135.00'),
            'remaining_amount': Decimal('0.00'),
        }
        defaults.update(overrides)
        return Order.objects.create(**defaults)

    def _mark_delivered(self, order, completed_at=None):
        order.status = 'delivered'
        order.rider_status = 'delivered'
        order.save(update_fields=['status', 'rider_status'])
        history = OrderStatusHistory.objects.create(
            order=order,
            status='delivered',
            previous_status='ready_for_delivery',
            changed_by=self.rider,
        )
        if completed_at is not None:
            OrderStatusHistory.objects.filter(pk=history.pk).update(created_at=completed_at)
        return history

    def test_non_rider_forbidden(self):
        response = self.non_rider_client.get('/api/riders/orders/history/?period=today')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delivery_history_included_with_work_type(self):
        order = self._create_order(
            delivery_rider=self.rider,
            status='delivered',
            rider_status='delivered',
        )
        self._mark_delivered(order, timezone.now())

        response = self.rider_client.get('/api/riders/orders/history/?period=today')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        orders = response.data['data']['orders']
        self.assertEqual(response.data['data']['count'], 1)
        self.assertEqual(orders[0]['id'], order.id)
        self.assertEqual(orders[0]['work_type'], 'delivery')
        self.assertIn('completed_at', orders[0])

    def test_measurement_history_included_while_order_in_progress(self):
        taken_at = timezone.now()
        order = self._create_order(
            measurement_rider=self.rider,
            status='in_progress',
            rider_status='measurement_taken',
            measurement_taken_at=taken_at,
        )

        response = self.rider_client.get('/api/riders/orders/history/?period=today')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        orders = response.data['data']['orders']
        self.assertEqual(response.data['data']['count'], 1)
        self.assertEqual(orders[0]['id'], order.id)
        self.assertEqual(orders[0]['work_type'], 'measurement')
        self.assertEqual(orders[0]['status'], 'in_progress')

    def test_same_rider_gets_two_rows_for_measurement_and_delivery(self):
        taken_at = timezone.now() - timedelta(hours=2)
        delivered_at = timezone.now()
        order = self._create_order(
            measurement_rider=self.rider,
            delivery_rider=self.rider,
            status='in_progress',
            rider_status='measurement_taken',
            measurement_taken_at=taken_at,
        )
        self._mark_delivered(order, delivered_at)

        response = self.rider_client.get('/api/riders/orders/history/?period=today')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        orders = response.data['data']['orders']
        self.assertEqual(response.data['data']['count'], 2)
        self.assertEqual({item['id'] for item in orders}, {order.id})
        work_types = {item['work_type'] for item in orders}
        self.assertEqual(work_types, {'measurement', 'delivery'})
        self.assertEqual(orders[0]['work_type'], 'delivery')

    def test_history_scoped_to_current_rider(self):
        own_order = self._create_order(
            delivery_rider=self.rider,
            status='delivered',
            rider_status='delivered',
        )
        self._mark_delivered(own_order, timezone.now())

        other_order = self._create_order(
            delivery_rider=self.other_rider,
            status='delivered',
            rider_status='delivered',
        )
        self._mark_delivered(other_order, timezone.now())

        response = self.rider_client.get('/api/riders/orders/history/?period=today')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order_ids = [item['id'] for item in response.data['data']['orders']]
        self.assertIn(own_order.id, order_ids)
        self.assertNotIn(other_order.id, order_ids)

    def test_history_period_today(self):
        today_order = self._create_order(
            delivery_rider=self.rider,
            status='delivered',
            rider_status='delivered',
        )
        self._mark_delivered(today_order, timezone.now())

        old_order = self._create_order(
            delivery_rider=self.rider,
            status='delivered',
            rider_status='delivered',
        )
        self._mark_delivered(old_order, timezone.now() - timedelta(days=3))

        response = self.rider_client.get('/api/riders/orders/history/?period=today')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order_ids = [item['id'] for item in response.data['data']['orders']]
        self.assertEqual(order_ids, [today_order.id])

    def test_history_period_yesterday(self):
        yesterday = timezone.now() - timedelta(days=1)
        yesterday_order = self._create_order(
            delivery_rider=self.rider,
            status='delivered',
            rider_status='delivered',
        )
        self._mark_delivered(yesterday_order, yesterday)

        today_order = self._create_order(
            delivery_rider=self.rider,
            status='delivered',
            rider_status='delivered',
        )
        self._mark_delivered(today_order, timezone.now())

        response = self.rider_client.get('/api/riders/orders/history/?period=yesterday')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order_ids = [item['id'] for item in response.data['data']['orders']]
        self.assertEqual(order_ids, [yesterday_order.id])

    def test_history_period_custom_range(self):
        start_day = timezone.localdate() - timedelta(days=10)
        in_range = self._create_order(
            delivery_rider=self.rider,
            status='delivered',
            rider_status='delivered',
        )
        self._mark_delivered(
            in_range,
            timezone.make_aware(datetime.combine(start_day + timedelta(days=2), datetime.min.time())),
        )

        out_of_range = self._create_order(
            delivery_rider=self.rider,
            status='delivered',
            rider_status='delivered',
        )
        self._mark_delivered(out_of_range, timezone.now() - timedelta(days=30))

        response = self.rider_client.get(
            '/api/riders/orders/history/',
            {
                'period': 'custom',
                'from_date': start_day.isoformat(),
                'to_date': (start_day + timedelta(days=5)).isoformat(),
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order_ids = [item['id'] for item in response.data['data']['orders']]
        self.assertEqual(order_ids, [in_range.id])

    def test_history_custom_range_requires_dates(self):
        response = self.rider_client.get('/api/riders/orders/history/?period=custom')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_history_defaults_to_past_six_months(self):
        recent = self._create_order(
            delivery_rider=self.rider,
            status='delivered',
            rider_status='delivered',
        )
        self._mark_delivered(recent, timezone.now() - timedelta(days=30))

        old = self._create_order(
            delivery_rider=self.rider,
            status='delivered',
            rider_status='delivered',
        )
        self._mark_delivered(old, timezone.now() - timedelta(days=200))

        response = self.rider_client.get('/api/riders/orders/history/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['period'], 'past_6_months')
        order_ids = [item['id'] for item in response.data['data']['orders']]
        self.assertIn(recent.id, order_ids)
        self.assertNotIn(old.id, order_ids)

    def test_history_search_by_order_number(self):
        order = self._create_order(
            delivery_rider=self.rider,
            status='delivered',
            rider_status='delivered',
        )
        self._mark_delivered(order, timezone.now())

        response = self.rider_client.get(
            f'/api/riders/orders/history/?period=today&search={order.order_number}'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['count'], 1)
        self.assertEqual(response.data['data']['orders'][0]['id'], order.id)
