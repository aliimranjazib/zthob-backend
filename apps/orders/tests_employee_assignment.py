from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.customers.models import Address
from apps.orders.actions import OrderActionManager
from apps.orders.models import Order, OrderItem
from apps.tailors.models import TailorEmployee, TailorProfile


User = get_user_model()


@override_settings(
    SECURE_SSL_REDIRECT=False,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}},
)
class OptionalStitchEmployeeAssignmentTest(APITestCase):
    """
    Rider-style assignment:
    - assigned employee → only that stitcher sees/works it
    - left empty → all can_stitch_orders employees see it
    """

    def setUp(self):
        self.customer = User.objects.create_user(
            username='opt_stitch_customer',
            password='testpass123',
            role='USER',
        )
        self.owner = User.objects.create_user(
            username='opt_stitch_owner',
            password='testpass123',
            role='TAILOR',
        )
        self.owner_profile, _ = TailorProfile.objects.get_or_create(
            user=self.owner,
            defaults={'shop_name': 'Opt Stitch Shop', 'shop_status': True},
        )
        self.stitcher_a_user = User.objects.create_user(
            username='stitcher_a',
            password='testpass123',
            role='TAILOR',
            first_name='Alice',
        )
        self.stitcher_a = TailorEmployee.objects.create(
            tailor=self.owner_profile,
            user=self.stitcher_a_user,
            roles=['stitcher'],
            can_manage_orders=False,
            can_stitch_orders=True,
            is_active=True,
        )
        self.stitcher_b_user = User.objects.create_user(
            username='stitcher_b',
            password='testpass123',
            role='TAILOR',
            first_name='Bob',
        )
        self.stitcher_b = TailorEmployee.objects.create(
            tailor=self.owner_profile,
            user=self.stitcher_b_user,
            roles=['stitcher'],
            can_manage_orders=False,
            can_stitch_orders=True,
            is_active=True,
        )
        self.address = Address.objects.create(
            user=self.customer,
            street='1 Stitch St',
            city='Riyadh',
            country='Saudi Arabia',
        )
        self.owner_client = APIClient()
        self.owner_client.force_authenticate(user=self.owner)
        self.a_client = APIClient()
        self.a_client.force_authenticate(user=self.stitcher_a_user)
        self.b_client = APIClient()
        self.b_client.force_authenticate(user=self.stitcher_b_user)

    def _create_ready_to_stitch(self, *, service_mode='home_delivery'):
        order = Order.objects.create(
            customer=self.customer,
            tailor=self.owner,
            order_type='fabric_with_stitching',
            service_mode=service_mode,
            payment_method='cod',
            payment_status='pending',
            status='confirmed',
            tailor_status='accepted',
            delivery_address=self.address,
            subtotal=Decimal('100.00'),
            total_amount=Decimal('100.00'),
            paid_amount=Decimal('0.00'),
            remaining_amount=Decimal('100.00'),
        )
        OrderItem.objects.create(
            order=order,
            fabric=None,
            quantity=1,
            unit_price=Decimal('100.00'),
            measurements={'chest': 42, 'length': 56, 'unit': 'cm'},
        )
        return order

    def _action_keys(self, order, *, role='TAILOR'):
        actions = OrderActionManager.get_available_actions(order, self.owner, requested_role=role)
        return [action['key'] for action in actions]

    def _create_waiting_for_rider_measurements(self):
        order = Order.objects.create(
            customer=self.customer,
            tailor=self.owner,
            order_type='fabric_with_stitching',
            service_mode='home_delivery',
            payment_method='cod',
            payment_status='pending',
            status='confirmed',
            tailor_status='accepted',
            rider_status='accepted',
            delivery_address=self.address,
            subtotal=Decimal('100.00'),
            total_amount=Decimal('100.00'),
            paid_amount=Decimal('0.00'),
            remaining_amount=Decimal('100.00'),
        )
        OrderItem.objects.create(
            order=order,
            fabric=None,
            quantity=1,
            unit_price=Decimal('100.00'),
            measurements={},
        )
        return order

    def test_assign_employee_hidden_while_waiting_for_rider_measurements(self):
        order = self._create_waiting_for_rider_measurements()
        self.assertNotIn('assign_employee', self._action_keys(order))

    def test_assign_employee_hidden_when_ready_to_stitch(self):
        order = self._create_ready_to_stitch()
        keys = self._action_keys(order)
        self.assertIn('start_stitching', keys)
        self.assertNotIn('assign_employee', keys)

    def test_assign_employee_hidden_after_mark_ready(self):
        order = self._create_ready_to_stitch()
        order.tailor_status = 'stitched'
        order.status = 'ready_for_delivery'
        order.save(update_fields=['tailor_status', 'status'])
        self.assertNotIn('assign_employee', self._action_keys(order))

    def test_assign_employee_available_during_active_stitching(self):
        order = self._create_ready_to_stitch()
        start = self.owner_client.post(
            f'/api/orders/{order.id}/action/',
            data={'action': 'start_stitching', 'role': 'TAILOR', 'data': {}},
            format='json',
        )
        self.assertEqual(start.status_code, status.HTTP_200_OK, start.data)
        order.refresh_from_db()
        self.assertIn('assign_employee', self._action_keys(order))

    def test_start_stitching_with_employee_hides_from_other_stitchers(self):
        order = self._create_ready_to_stitch(service_mode='home_delivery')

        response = self.owner_client.post(
            f'/api/orders/{order.id}/action/',
            data={
                'action': 'start_stitching',
                'role': 'TAILOR',
                'data': {'assigned_employee_id': self.stitcher_a.id},
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        order.refresh_from_db()
        self.assertEqual(order.assigned_employee_id, self.stitcher_a.id)

        a_list = self.a_client.get('/api/orders/tailor/my-orders/')
        b_list = self.b_client.get('/api/orders/tailor/my-orders/')
        self.assertEqual(a_list.status_code, status.HTTP_200_OK)
        self.assertEqual(b_list.status_code, status.HTTP_200_OK)
        self.assertIn(order.id, [o['id'] for o in a_list.data['data']])
        self.assertNotIn(order.id, [o['id'] for o in b_list.data['data']])

        denied = self.b_client.post(
            f'/api/orders/{order.id}/action/',
            data={'action': 'finish_stitching', 'role': 'TAILOR', 'data': {}},
            format='json',
        )
        # Order still stitching_started — B cannot finish
        self.assertIn(denied.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_400_BAD_REQUEST))

    def test_start_stitching_without_employee_is_open_to_all_stitchers(self):
        order = self._create_ready_to_stitch(service_mode='walk_in')

        response = self.owner_client.post(
            f'/api/orders/{order.id}/action/',
            data={
                'action': 'start_stitching',
                'role': 'TAILOR',
                'data': {},  # leave empty → open
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        order.refresh_from_db()
        self.assertIsNone(order.assigned_employee_id)

        a_list = self.a_client.get('/api/orders/tailor/available-orders/')
        b_list = self.b_client.get('/api/orders/tailor/available-orders/')
        self.assertIn(order.id, [o['id'] for o in a_list.data['data']])
        self.assertIn(order.id, [o['id'] for o in b_list.data['data']])

        # Either stitcher can continue stitching
        start_b = self.b_client.post(
            f'/api/orders/{order.id}/action/',
            data={'action': 'finish_stitching', 'role': 'TAILOR', 'data': {}},
            format='json',
        )
        self.assertEqual(start_b.status_code, status.HTTP_200_OK, start_b.data)

    def test_clear_assignment_reopens_to_all_stitchers(self):
        order = self._create_ready_to_stitch(service_mode='home_delivery')
        order.assigned_employee = self.stitcher_a
        order.tailor_status = 'stitching_started'
        order.status = 'in_progress'
        order.save(update_fields=['assigned_employee', 'tailor_status', 'status'])

        response = self.owner_client.post(
            f'/api/orders/{order.id}/action/',
            data={
                'action': 'assign_employee',
                'role': 'TAILOR',
                'data': {'assigned_employee_id': None},
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        order.refresh_from_db()
        self.assertIsNone(order.assigned_employee_id)

        b_list = self.b_client.get('/api/orders/tailor/my-orders/')
        self.assertIn(order.id, [o['id'] for o in b_list.data['data']])

    def test_assignable_employees_filter(self):
        no_stitch = TailorEmployee.objects.create(
            tailor=self.owner_profile,
            user=User.objects.create_user(
                username='no_stitch_emp',
                password='testpass123',
                role='TAILOR',
            ),
            roles=['receptionist'],
            can_manage_orders=True,
            can_stitch_orders=False,
            is_active=True,
        )
        response = self.owner_client.get(
            '/api/tailors/employees/?assignable_for_stitching=true'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [e['id'] for e in response.data['data']]
        self.assertIn(self.stitcher_a.id, ids)
        self.assertIn(self.stitcher_b.id, ids)
        self.assertNotIn(no_stitch.id, ids)
