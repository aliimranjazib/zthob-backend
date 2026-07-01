from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from apps.customers.models import Address
from apps.orders.models import Order, OrderItem
from apps.tailors.models import TailorEmployee, TailorProfile


User = get_user_model()


@override_settings(
    SECURE_SSL_REDIRECT=False,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}},
)
class TailorEmployeeOrderAccessTest(APITestCase):
    def setUp(self):
        self.customer = User.objects.create_user(
            username='emp_order_customer',
            password='testpass123',
            role='USER',
        )
        self.owner = User.objects.create_user(
            username='emp_order_owner',
            password='testpass123',
            role='TAILOR',
        )
        self.owner_profile, _ = TailorProfile.objects.get_or_create(
            user=self.owner,
            defaults={
                'shop_name': 'Employee Order Shop',
                'shop_status': True,
            },
        )
        self.employee_user = User.objects.create_user(
            username='emp_order_staff',
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
            street='123 Employee St',
            city='Riyadh',
            country='Saudi Arabia',
        )
        self.employee_client = APIClient()
        self.employee_client.force_authenticate(user=self.employee_user)

    def _create_order(self, **overrides):
        defaults = {
            'customer': self.customer,
            'tailor': self.owner,
            'order_type': 'fabric_with_stitching',
            'service_mode': 'home_delivery',
            'payment_method': 'cod',
            'payment_status': 'pending',
            'status': 'pending',
            'tailor_status': 'none',
            'delivery_address': self.address,
            'subtotal': Decimal('100.00'),
            'tax_amount': Decimal('15.00'),
            'delivery_fee': Decimal('20.00'),
            'total_amount': Decimal('135.00'),
            'paid_amount': Decimal('0.00'),
            'remaining_amount': Decimal('135.00'),
        }
        defaults.update(overrides)
        return Order.objects.create(**defaults)

    def test_employee_can_accept_home_delivery_order(self):
        order = self._create_order()

        response = self.employee_client.post(
            f'/api/orders/{order.id}/action/',
            data={'action': 'accept_order', 'role': 'TAILOR', 'data': {}},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        self.assertEqual(order.tailor_id, self.owner.id)
        self.assertEqual(order.tailor_status, 'accepted')

    def test_employee_can_collect_walk_in_order(self):
        order = self._create_order(
            service_mode='walk_in',
            status='ready_for_pickup',
            tailor_status='stitched',
            payment_status='paid',
            paid_amount=Decimal('135.00'),
            remaining_amount=Decimal('0.00'),
        )

        response = self.employee_client.post(
            f'/api/orders/{order.id}/action/',
            data={'action': 'collect_order', 'role': 'TAILOR', 'data': {}},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        self.assertEqual(order.status, 'collected')

    def test_employee_can_collect_cash_for_walk_in_order(self):
        order = self._create_order(
            service_mode='walk_in',
            status='ready_for_pickup',
            tailor_status='stitched',
            payment_status='pending',
            paid_amount=Decimal('0.00'),
            remaining_amount=Decimal('135.00'),
        )

        response = self.employee_client.post(
            f'/api/orders/{order.id}/action/',
            data={'action': 'collect_cash_payment', 'role': 'TAILOR', 'data': {}},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        self.assertEqual(order.payment_status, 'paid')

    def test_employee_without_order_permission_cannot_accept(self):
        self.employee.can_manage_orders = False
        self.employee.save(update_fields=['can_manage_orders'])
        order = self._create_order()

        response = self.employee_client.post(
            f'/api/orders/{order.id}/action/',
            data={'action': 'accept_order', 'role': 'TAILOR', 'data': {}},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        order.refresh_from_db()
        self.assertEqual(order.tailor_status, 'none')


@override_settings(
    SECURE_SSL_REDIRECT=False,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}},
)
class TailorPosEmployeeMeasurementAccessTest(APITestCase):
    def setUp(self):
        self.customer = User.objects.create_user(
            username='pos_measure_customer',
            password='testpass123',
            role='USER',
        )
        self.owner = User.objects.create_user(
            username='pos_measure_owner',
            password='testpass123',
            role='TAILOR',
        )
        self.owner_profile, _ = TailorProfile.objects.get_or_create(
            user=self.owner,
            defaults={
                'shop_name': 'POS Measurement Shop',
                'shop_status': True,
            },
        )
        self.pos_employee_user = User.objects.create_user(
            username='pos_measure_staff',
            password='testpass123',
            role='TAILOR',
        )
        self.pos_employee = TailorEmployee.objects.create(
            tailor=self.owner_profile,
            user=self.pos_employee_user,
            roles=['pos'],
            can_manage_pos=True,
            can_manage_orders=False,
            is_active=True,
        )
        self.pos_client = APIClient()
        self.pos_client.force_authenticate(user=self.pos_employee_user)

    def _create_walk_in_order_needing_measurements(self):
        order = Order.objects.create(
            customer=self.customer,
            tailor=self.owner,
            order_type='fabric_with_stitching',
            service_mode='walk_in',
            payment_method='cod',
            payment_status='pending',
            status='confirmed',
            tailor_status='accepted',
            subtotal=Decimal('100.00'),
            tax_amount=Decimal('15.00'),
            delivery_fee=Decimal('0.00'),
            total_amount=Decimal('115.00'),
            paid_amount=Decimal('0.00'),
            remaining_amount=Decimal('115.00'),
        )
        OrderItem.objects.create(
            order=order,
            quantity=1,
            unit_price=Decimal('100.00'),
        )
        return order

    def test_pos_employee_sees_record_measurements_on_walk_in_order(self):
        order = self._create_walk_in_order_needing_measurements()

        response = self.pos_client.get(
            f'/api/tailors/pos/customers/{self.customer.id}/orders/{order.id}/'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        status_info = response.data['data']['status_info']
        action_values = [action['value'] for action in status_info['next_available_actions']]
        available_action_values = [
            action['key'] for action in status_info['available_actions']
        ]
        self.assertIn('record_measurements', action_values)
        self.assertIn('record_measurements', available_action_values)
        self.assertNotIn('accepted', action_values)
        self.assertNotIn('accept_order', available_action_values)

    def test_pos_employee_can_record_measurements_for_walk_in_order(self):
        order = self._create_walk_in_order_needing_measurements()

        response = self.pos_client.post(
            f'/api/orders/{order.id}/action/',
            data={
                'action': 'record_measurements',
                'role': 'TAILOR',
                'data': {'measurements': {'chest': 40, 'length': 58}},
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        self.assertTrue(order.all_items_have_measurements)

    def test_pos_employee_cannot_accept_walk_in_order(self):
        order = self._create_walk_in_order_needing_measurements()
        order.status = 'pending'
        order.tailor_status = 'none'
        order.save(update_fields=['status', 'tailor_status'])

        response = self.pos_client.post(
            f'/api/orders/{order.id}/action/',
            data={'action': 'accept_order', 'role': 'TAILOR', 'data': {}},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        order.refresh_from_db()
        self.assertEqual(order.tailor_status, 'none')
