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
