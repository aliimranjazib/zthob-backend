from datetime import datetime, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from apps.customers.models import Address
from apps.orders.models import Order, OrderStatusHistory
from apps.tailors.models import TailorEmployee, TailorProfile


User = get_user_model()


@override_settings(
    SECURE_SSL_REDIRECT=False,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}},
)
class TailorOrderHistoryViewTest(APITestCase):
    def setUp(self):
        self.customer = User.objects.create_user(
            username='history_customer',
            password='testpass123',
            role='USER',
            first_name='Ali',
            last_name='Ahmed',
        )
        self.owner = User.objects.create_user(
            username='history_owner',
            password='testpass123',
            role='TAILOR',
        )
        self.other_owner = User.objects.create_user(
            username='history_other_owner',
            password='testpass123',
            role='TAILOR',
        )
        self.owner_profile, _ = TailorProfile.objects.get_or_create(
            user=self.owner,
            defaults={'shop_name': 'History Shop', 'shop_status': True},
        )
        TailorProfile.objects.get_or_create(
            user=self.other_owner,
            defaults={'shop_name': 'Other Shop', 'shop_status': True},
        )
        self.employee_user = User.objects.create_user(
            username='history_employee',
            password='testpass123',
            role='TAILOR',
        )
        self.employee = TailorEmployee.objects.create(
            tailor=self.owner_profile,
            user=self.employee_user,
            roles=['receptionist'],
            can_manage_orders=True,
            is_active=True,
        )
        self.address = Address.objects.create(
            user=self.customer,
            street='123 History St',
            city='Riyadh',
            country='Saudi Arabia',
        )
        self.owner_client = APIClient()
        self.owner_client.force_authenticate(user=self.owner)
        self.employee_client = APIClient()
        self.employee_client.force_authenticate(user=self.employee_user)

    def _create_order(self, tailor=None, **overrides):
        defaults = {
            'customer': self.customer,
            'tailor': tailor or self.owner,
            'order_type': 'fabric_with_stitching',
            'service_mode': 'home_delivery',
            'payment_method': 'cod',
            'payment_status': 'paid',
            'status': 'delivered',
            'tailor_status': 'stitched',
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

    def _mark_completed(self, order, completed_status='delivered', completed_at=None):
        order.status = completed_status
        order.save(update_fields=['status'])
        history = OrderStatusHistory.objects.create(
            order=order,
            status=completed_status,
            previous_status='ready_for_delivery' if completed_status == 'delivered' else 'ready_for_pickup',
            changed_by=self.owner,
        )
        if completed_at is not None:
            OrderStatusHistory.objects.filter(pk=history.pk).update(created_at=completed_at)
        return history

    def test_history_returns_only_completed_orders(self):
        completed = self._create_order(status='delivered')
        self._mark_completed(completed, 'delivered', timezone.now())

        active = self._create_order(status='in_progress', tailor_status='accepted')
        cancelled = self._create_order(status='cancelled')

        response = self.owner_client.get('/api/orders/tailor/history/?period=past_6_months')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order_ids = [item['id'] for item in response.data['data']['orders']]
        self.assertIn(completed.id, order_ids)
        self.assertNotIn(active.id, order_ids)
        self.assertNotIn(cancelled.id, order_ids)

    def test_history_includes_collected_walk_in_orders(self):
        order = self._create_order(service_mode='walk_in', status='collected')
        self._mark_completed(order, 'collected', timezone.now())

        response = self.owner_client.get('/api/orders/tailor/history/?period=today')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['count'], 1)
        self.assertEqual(response.data['data']['orders'][0]['status'], 'collected')
        self.assertIn('completed_at', response.data['data']['orders'][0])

    def test_history_period_today(self):
        today_order = self._create_order(status='delivered')
        self._mark_completed(today_order, 'delivered', timezone.now())

        old_order = self._create_order(status='delivered')
        self._mark_completed(old_order, 'delivered', timezone.now() - timedelta(days=3))

        response = self.owner_client.get('/api/orders/tailor/history/?period=today')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order_ids = [item['id'] for item in response.data['data']['orders']]
        self.assertEqual(order_ids, [today_order.id])

    def test_history_period_yesterday(self):
        yesterday = timezone.now() - timedelta(days=1)
        yesterday_order = self._create_order(status='delivered')
        self._mark_completed(yesterday_order, 'delivered', yesterday)

        today_order = self._create_order(status='delivered')
        self._mark_completed(today_order, 'delivered', timezone.now())

        response = self.owner_client.get('/api/orders/tailor/history/?period=yesterday')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order_ids = [item['id'] for item in response.data['data']['orders']]
        self.assertEqual(order_ids, [yesterday_order.id])

    def test_history_period_custom_range(self):
        start_day = timezone.localdate() - timedelta(days=10)
        in_range = self._create_order(status='delivered')
        self._mark_completed(
            in_range,
            'delivered',
            timezone.make_aware(datetime.combine(start_day + timedelta(days=2), datetime.min.time())),
        )

        out_of_range = self._create_order(status='delivered')
        self._mark_completed(out_of_range, 'delivered', timezone.now() - timedelta(days=30))

        response = self.owner_client.get(
            '/api/orders/tailor/history/',
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
        response = self.owner_client.get('/api/orders/tailor/history/?period=custom')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_history_defaults_to_past_six_months(self):
        recent = self._create_order(status='delivered')
        self._mark_completed(recent, 'delivered', timezone.now() - timedelta(days=30))

        old = self._create_order(status='delivered')
        self._mark_completed(old, 'delivered', timezone.now() - timedelta(days=200))

        response = self.owner_client.get('/api/orders/tailor/history/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['period'], 'past_6_months')
        order_ids = [item['id'] for item in response.data['data']['orders']]
        self.assertIn(recent.id, order_ids)
        self.assertNotIn(old.id, order_ids)

    def test_employee_sees_shop_owner_completed_orders(self):
        order = self._create_order(status='delivered')
        self._mark_completed(order, 'delivered', timezone.now())

        response = self.employee_client.get('/api/orders/tailor/history/?period=today')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['count'], 1)

    def test_history_scoped_to_current_tailor_shop(self):
        own_order = self._create_order(status='delivered')
        self._mark_completed(own_order, 'delivered', timezone.now())

        other_order = self._create_order(tailor=self.other_owner, status='delivered')
        self._mark_completed(other_order, 'delivered', timezone.now())

        response = self.owner_client.get('/api/orders/tailor/history/?period=today')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order_ids = [item['id'] for item in response.data['data']['orders']]
        self.assertIn(own_order.id, order_ids)
        self.assertNotIn(other_order.id, order_ids)

    def test_history_search_by_order_number(self):
        order = self._create_order(status='delivered')
        self._mark_completed(order, 'delivered', timezone.now())

        response = self.owner_client.get(
            f'/api/orders/tailor/history/?period=today&search={order.order_number}'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['count'], 1)
        self.assertEqual(response.data['data']['orders'][0]['id'], order.id)
