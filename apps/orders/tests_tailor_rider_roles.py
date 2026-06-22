from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.orders.models import Order, OrderItem
from apps.riders.models import RiderProfile, RiderProfileReview
from apps.tailors.models import TailorProfile


User = get_user_model()


@override_settings(
    SECURE_SSL_REDIRECT=False,
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    },
)
class TailorRiderRoleAssignmentTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.notification_patchers = [
            patch('apps.notifications.tasks.send_order_status_notification_task.delay'),
            patch('apps.notifications.tasks.send_rider_status_notification_task.delay'),
            patch('apps.notifications.tasks.send_tailor_status_notification_task.delay'),
            patch('apps.notifications.services.NotificationService.send_new_order_broadcast'),
        ]
        for patcher in self.notification_patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

        self.customer = User.objects.create_user(
            username='role_customer',
            password='testpass123',
            role='USER',
        )
        self.tailor = User.objects.create_user(
            username='role_tailor',
            password='testpass123',
            role='TAILOR',
        )
        tailor_profile, _ = TailorProfile.objects.get_or_create(user=self.tailor)
        tailor_profile.shop_name = 'Role Tailor'
        tailor_profile.shop_status = True
        tailor_profile.save(update_fields=['shop_name', 'shop_status'])
        self.measurement_rider = self._create_approved_rider('measurement_rider')
        self.delivery_rider = self._create_approved_rider('delivery_rider')

    def _create_approved_rider(self, username):
        rider = User.objects.create_user(
            username=username,
            password='testpass123',
            role='RIDER',
        )
        profile, _ = RiderProfile.objects.get_or_create(user=rider)
        profile.full_name = username
        profile.save(update_fields=['full_name'])
        review, _ = RiderProfileReview.objects.get_or_create(profile=profile)
        review.review_status = 'approved'
        review.save(update_fields=['review_status'])
        return rider

    def _create_stitching_order(self, measurements=None):
        order = Order.objects.create(
            customer=self.customer,
            tailor=self.tailor,
            order_type='fabric_with_stitching',
            service_mode='home_delivery',
            status='pending',
            tailor_status='none',
            rider_status='none',
            payment_status='paid',
            total_amount=Decimal('100.00'),
            paid_amount=Decimal('100.00'),
            remaining_amount=Decimal('0.00'),
        )
        OrderItem.objects.create(
            order=order,
            fabric=None,
            quantity=1,
            unit_price=Decimal('100.00'),
            total_price=Decimal('100.00'),
            measurements=measurements or {},
        )
        return order

    def test_tailor_accept_measured_order_does_not_assign_initial_rider(self):
        order = self._create_stitching_order(measurements={'chest': 42})
        self.client.force_authenticate(user=self.tailor)

        response = self.client.post(
            f'/api/tailors/orders/{order.id}/accept/',
            {'assigned_rider_id': self.delivery_rider.id},
            format='json',
        )

        self.assertEqual(response.status_code, 200, response.data)
        order.refresh_from_db()
        self.assertEqual(order.tailor_status, 'accepted')
        self.assertEqual(order.status, 'confirmed')
        self.assertIsNone(order.rider)
        self.assertIsNone(order.assigned_rider)
        self.assertIsNone(order.measurement_rider)
        self.assertIsNone(order.delivery_rider)

    def test_tailor_accept_missing_measurements_assigns_measurement_rider(self):
        order = self._create_stitching_order()
        self.client.force_authenticate(user=self.tailor)

        response = self.client.post(
            f'/api/tailors/orders/{order.id}/accept/',
            {
                'assigned_rider_id': self.measurement_rider.id,
                'rider_assignment_type': 'measurement',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 200, response.data)
        order.refresh_from_db()
        self.assertEqual(order.tailor_status, 'accepted')
        self.assertEqual(order.measurement_rider, self.measurement_rider)
        self.assertEqual(order.assigned_rider, self.measurement_rider)
        self.assertEqual(order.rider, self.measurement_rider)
        self.assertIsNone(order.delivery_rider)

    def test_assigned_measurement_rider_sees_new_job_in_available_orders(self):
        order = self._create_stitching_order()
        self.client.force_authenticate(user=self.tailor)
        accept_response = self.client.post(
            f'/api/tailors/orders/{order.id}/accept/',
            {
                'assigned_rider_id': self.measurement_rider.id,
                'rider_assignment_type': 'measurement',
            },
            format='json',
        )
        self.assertEqual(accept_response.status_code, 200, accept_response.data)

        self.client.force_authenticate(user=self.measurement_rider)
        response = self.client.get('/api/riders/orders/available/')

        self.assertEqual(response.status_code, 200, response.data)
        order_item = next((item for item in response.data['data'] if item['id'] == order.id), None)
        self.assertIsNotNone(order_item)
        self.assertEqual(order_item['rider_assignment_type'], 'measurement')

    def test_ready_for_delivery_assigns_delivery_rider_and_resets_measurement_status(self):
        order = self._create_stitching_order(measurements={'chest': 42})
        order.tailor_status = 'stitched'
        order.status = 'in_progress'
        order.rider_status = 'measurement_taken'
        order.measurement_rider = self.measurement_rider
        order.rider = self.measurement_rider
        order.assigned_rider = self.measurement_rider
        order.save()

        self.client.force_authenticate(user=self.tailor)
        response = self.client.patch(
            f'/api/tailors/orders/{order.id}/update-status/',
            {
                'tailor_status': 'ready_for_delivery',
                'assigned_rider_id': self.delivery_rider.id,
                'rider_assignment_type': 'delivery',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 200, response.data)
        order.refresh_from_db()
        self.assertEqual(order.status, 'ready_for_delivery')
        self.assertEqual(order.delivery_rider, self.delivery_rider)
        self.assertEqual(order.assigned_rider, self.delivery_rider)
        self.assertEqual(order.rider, self.delivery_rider)
        self.assertEqual(order.rider_status, 'none')
        self.assertEqual(order.measurement_rider, self.measurement_rider)

    def test_delivery_rider_sees_order_in_my_orders_after_tailor_assignment(self):
        order = self._create_stitching_order(measurements={'chest': 42})
        order.tailor_status = 'stitched'
        order.status = 'in_progress'
        order.rider_status = 'measurement_taken'
        order.measurement_rider = self.measurement_rider
        order.rider = self.measurement_rider
        order.assigned_rider = self.measurement_rider
        order.save()

        self.client.force_authenticate(user=self.tailor)
        assign_response = self.client.patch(
            f'/api/tailors/orders/{order.id}/update-status/',
            {
                'tailor_status': 'ready_for_delivery',
                'assigned_rider_id': self.delivery_rider.id,
                'rider_assignment_type': 'delivery',
            },
            format='json',
        )
        self.assertEqual(assign_response.status_code, 200, assign_response.data)

        self.client.force_authenticate(user=self.delivery_rider)
        response = self.client.get('/api/riders/orders/my-orders/')

        self.assertEqual(response.status_code, 200, response.data)
        order_ids = [item['id'] for item in response.data['data']]
        self.assertIn(order.id, order_ids)
        order_item = next(item for item in response.data['data'] if item['id'] == order.id)
        self.assertEqual(order_item['rider_assignment_type'], 'delivery')

    def test_delivery_rider_sees_order_in_available_orders_after_tailor_assignment(self):
        order = self._create_stitching_order(measurements={'chest': 42})
        order.tailor_status = 'stitched'
        order.status = 'in_progress'
        order.rider_status = 'measurement_taken'
        order.measurement_rider = self.measurement_rider
        order.rider = self.measurement_rider
        order.assigned_rider = self.measurement_rider
        order.save()

        self.client.force_authenticate(user=self.tailor)
        assign_response = self.client.patch(
            f'/api/tailors/orders/{order.id}/update-status/',
            {
                'tailor_status': 'ready_for_delivery',
                'assigned_rider_id': self.delivery_rider.id,
                'rider_assignment_type': 'delivery',
            },
            format='json',
        )
        self.assertEqual(assign_response.status_code, 200, assign_response.data)

        self.client.force_authenticate(user=self.delivery_rider)
        response = self.client.get('/api/riders/orders/available/')

        self.assertEqual(response.status_code, 200, response.data)
        order_item = next((item for item in response.data['data'] if item['id'] == order.id), None)
        self.assertIsNotNone(order_item)
        self.assertEqual(order_item['rider_assignment_type'], 'delivery')

    def test_other_rider_does_not_see_assigned_delivery_job_in_available_orders(self):
        other_rider = self._create_approved_rider('other_delivery_rider')
        order = self._create_stitching_order(measurements={'chest': 42})
        order.tailor_status = 'stitched'
        order.status = 'ready_for_delivery'
        order.rider_status = 'none'
        order.measurement_rider = self.measurement_rider
        order.delivery_rider = self.delivery_rider
        order.rider = self.delivery_rider
        order.assigned_rider = self.delivery_rider
        order.save()

        self.client.force_authenticate(user=other_rider)
        response = self.client.get('/api/riders/orders/available/')

        self.assertEqual(response.status_code, 200, response.data)
        self.assertNotIn(order.id, [item['id'] for item in response.data['data']])

    def test_delivery_rider_can_open_detail_before_accepting_delivery_assignment(self):
        order = self._create_stitching_order(measurements={'chest': 42})
        order.tailor_status = 'stitched'
        order.status = 'ready_for_delivery'
        order.rider_status = 'none'
        order.measurement_rider = self.measurement_rider
        order.delivery_rider = self.delivery_rider
        order.rider = self.delivery_rider
        order.assigned_rider = self.delivery_rider
        order.save()

        self.client.force_authenticate(user=self.delivery_rider)
        response = self.client.get(f'/api/riders/orders/{order.id}/')

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['data']['id'], order.id)
        self.assertEqual(response.data['data']['rider_assignment_type'], 'delivery')

    def test_delivery_rider_sees_stale_legacy_measurement_assignment_in_my_orders(self):
        order = self._create_stitching_order(measurements={'chest': 42})
        order.tailor_status = 'stitched'
        order.status = 'ready_for_delivery'
        order.rider_status = 'measurement_taken'
        order.measurement_rider = self.measurement_rider
        order.delivery_rider = self.delivery_rider
        order.rider = self.measurement_rider
        order.assigned_rider = self.measurement_rider
        order.save()

        self.client.force_authenticate(user=self.delivery_rider)
        response = self.client.get('/api/riders/orders/my-orders/')

        self.assertEqual(response.status_code, 200, response.data)
        order_ids = [item['id'] for item in response.data['data']]
        self.assertIn(order.id, order_ids)
        order_item = next(item for item in response.data['data'] if item['id'] == order.id)
        self.assertEqual(order_item['rider_assignment_type'], 'delivery')

    def test_delivery_rider_can_accept_stale_legacy_measurement_assignment(self):
        order = self._create_stitching_order(measurements={'chest': 42})
        order.tailor_status = 'stitched'
        order.status = 'ready_for_delivery'
        order.rider_status = 'measurement_taken'
        order.measurement_rider = self.measurement_rider
        order.delivery_rider = self.delivery_rider
        order.rider = self.measurement_rider
        order.assigned_rider = self.measurement_rider
        order.save()

        self.client.force_authenticate(user=self.delivery_rider)
        response = self.client.post(f'/api/riders/orders/{order.id}/accept/')

        self.assertEqual(response.status_code, 200, response.data)
        order.refresh_from_db()
        self.assertEqual(order.rider, self.delivery_rider)
        self.assertEqual(order.assigned_rider, self.delivery_rider)
        self.assertEqual(order.delivery_rider, self.delivery_rider)
        self.assertEqual(order.measurement_rider, self.measurement_rider)
        self.assertEqual(order.rider_status, 'accepted')

    def test_measurement_rider_cannot_accept_delivery_after_delivery_rider_assigned(self):
        order = self._create_stitching_order(measurements={'chest': 42})
        order.tailor_status = 'stitched'
        order.status = 'ready_for_delivery'
        order.rider_status = 'none'
        order.measurement_rider = self.measurement_rider
        order.delivery_rider = self.delivery_rider
        order.rider = self.measurement_rider
        order.assigned_rider = self.measurement_rider
        order.save()

        self.client.force_authenticate(user=self.measurement_rider)
        response = self.client.patch(
            f'/api/riders/orders/{order.id}/update-status/',
            {'rider_status': 'accepted'},
            format='json',
        )

        self.assertEqual(response.status_code, 403, response.data)
        order.refresh_from_db()
        self.assertEqual(order.rider_status, 'none')

    def test_full_measurement_then_different_delivery_rider_action_flow(self):
        order = self._create_stitching_order()

        self.client.force_authenticate(user=self.tailor)
        accept_response = self.client.post(
            f'/api/tailors/orders/{order.id}/accept/',
            {
                'assigned_rider_id': self.measurement_rider.id,
                'rider_assignment_type': 'measurement',
            },
            format='json',
        )
        self.assertEqual(accept_response.status_code, 200, accept_response.data)

        self.client.force_authenticate(user=self.measurement_rider)
        measurement_accept_response = self.client.post(
            f'/api/orders/{order.id}/action/',
            {'action': 'accept_order', 'role': 'RIDER'},
            format='json',
        )
        self.assertEqual(measurement_accept_response.status_code, 200, measurement_accept_response.data)

        start_measuring_response = self.client.post(
            f'/api/orders/{order.id}/action/',
            {'action': 'start_measuring', 'role': 'RIDER'},
            format='json',
        )
        self.assertEqual(start_measuring_response.status_code, 200, start_measuring_response.data)

        measurements_response = self.client.post(
            f'/api/orders/{order.id}/action/',
            {
                'action': 'record_measurements',
                'role': 'RIDER',
                'data': {'measurements': {'chest': 42, 'length': 58}},
            },
            format='json',
        )
        self.assertEqual(measurements_response.status_code, 200, measurements_response.data)

        self.client.force_authenticate(user=self.tailor)
        start_stitching_response = self.client.post(
            f'/api/orders/{order.id}/action/',
            {
                'action': 'start_stitching',
                'role': 'TAILOR',
                'data': {'stitching_completion_date': '2026-06-25'},
            },
            format='json',
        )
        self.assertEqual(start_stitching_response.status_code, 200, start_stitching_response.data)

        finish_stitching_response = self.client.post(
            f'/api/orders/{order.id}/action/',
            {'action': 'finish_stitching', 'role': 'TAILOR'},
            format='json',
        )
        self.assertEqual(finish_stitching_response.status_code, 200, finish_stitching_response.data)

        mark_ready_response = self.client.post(
            f'/api/orders/{order.id}/action/',
            {
                'action': 'mark_ready',
                'role': 'TAILOR',
                'data': {'assigned_rider_id': self.delivery_rider.id},
            },
            format='json',
        )
        self.assertEqual(mark_ready_response.status_code, 200, mark_ready_response.data)

        self.client.force_authenticate(user=self.delivery_rider)
        my_orders_response = self.client.get('/api/riders/orders/my-orders/')
        self.assertEqual(my_orders_response.status_code, 200, my_orders_response.data)
        self.assertIn(order.id, [item['id'] for item in my_orders_response.data['data']])

        delivery_accept_response = self.client.post(
            f'/api/orders/{order.id}/action/',
            {'action': 'accept_order', 'role': 'RIDER'},
            format='json',
        )
        self.assertEqual(delivery_accept_response.status_code, 200, delivery_accept_response.data)

        pickup_response = self.client.post(
            f'/api/orders/{order.id}/action/',
            {'action': 'pickup_order', 'role': 'RIDER'},
            format='json',
        )
        self.assertEqual(pickup_response.status_code, 200, pickup_response.data)

        start_delivery_response = self.client.post(
            f'/api/orders/{order.id}/action/',
            {'action': 'start_delivery', 'role': 'RIDER'},
            format='json',
        )
        self.assertEqual(start_delivery_response.status_code, 200, start_delivery_response.data)

        delivered_response = self.client.post(
            f'/api/orders/{order.id}/action/',
            {'action': 'mark_delivered', 'role': 'RIDER'},
            format='json',
        )
        self.assertEqual(delivered_response.status_code, 200, delivered_response.data)

        order.refresh_from_db()
        self.assertEqual(order.measurement_rider, self.measurement_rider)
        self.assertEqual(order.delivery_rider, self.delivery_rider)
        self.assertEqual(order.rider, self.delivery_rider)
        self.assertEqual(order.status, 'delivered')
        self.assertEqual(order.rider_status, 'delivered')
