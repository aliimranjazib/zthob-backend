from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.orders.models import Order, OrderItem
from apps.riders.models import RiderProfile, RiderProfileReview, TailorRiderAssociation
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
class TailorRiderCapabilityTest(TestCase):
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
            username='cap_customer',
            password='testpass123',
            role='USER',
        )
        self.tailor = User.objects.create_user(
            username='cap_tailor',
            password='testpass123',
            role='TAILOR',
        )
        tailor_profile, _ = TailorProfile.objects.get_or_create(user=self.tailor)
        tailor_profile.shop_name = 'Capability Tailor'
        tailor_profile.shop_status = True
        tailor_profile.save(update_fields=['shop_name', 'shop_status'])

        self.rider = self._create_approved_rider('cap_rider')
        self.association = TailorRiderAssociation.objects.create(
            tailor=self.tailor,
            rider=self.rider,
            is_active=True,
        )

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
            quantity=1,
            unit_price=Decimal('100.00'),
            total_price=Decimal('100.00'),
            measurements=measurements or {},
        )
        return order

    def test_tailor_my_riders_shows_capabilities(self):
        self.client.force_authenticate(user=self.tailor)

        response = self.client.get('/api/riders/tailor/my-riders/')

        self.assertEqual(response.status_code, 200, response.data)
        rider_data = response.data['data']['riders'][0]
        self.assertTrue(rider_data['can_take_measurements'])
        self.assertTrue(rider_data['can_do_delivery'])

    def test_tailor_can_update_rider_capabilities(self):
        self.client.force_authenticate(user=self.tailor)

        response = self.client.patch(
            f'/api/riders/tailor/my-riders/{self.rider.id}/',
            {
                'can_take_measurements': True,
                'can_do_delivery': False,
                'nickname': 'Measure Pro',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.association.refresh_from_db()
        self.assertTrue(self.association.can_take_measurements)
        self.assertFalse(self.association.can_do_delivery)
        self.assertEqual(self.association.nickname, 'Measure Pro')

    def test_tailor_cannot_disable_all_rider_capabilities(self):
        self.client.force_authenticate(user=self.tailor)

        response = self.client.patch(
            f'/api/riders/tailor/my-riders/{self.rider.id}/',
            {
                'can_take_measurements': False,
                'can_do_delivery': False,
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400, response.data)

    def test_measurement_only_rider_cannot_be_assigned_for_delivery(self):
        self.association.can_take_measurements = True
        self.association.can_do_delivery = False
        self.association.save(update_fields=['can_take_measurements', 'can_do_delivery', 'updated_at'])
        order = self._create_stitching_order(measurements={'chest': 42})
        order.tailor_status = 'stitched'
        order.status = 'in_progress'
        order.save(update_fields=['tailor_status', 'status', 'updated_at'])

        self.client.force_authenticate(user=self.tailor)
        response = self.client.patch(
            f'/api/tailors/orders/{order.id}/update-status/',
            {
                'tailor_status': 'ready_for_delivery',
                'assigned_rider_id': self.rider.id,
                'rider_assignment_type': 'delivery',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn('not enabled for delivery', response.data['message'].lower())

    def test_delivery_only_rider_cannot_be_assigned_for_measurement(self):
        self.association.can_take_measurements = False
        self.association.can_do_delivery = True
        self.association.save(update_fields=['can_take_measurements', 'can_do_delivery', 'updated_at'])
        order = self._create_stitching_order()

        self.client.force_authenticate(user=self.tailor)
        response = self.client.post(
            f'/api/tailors/orders/{order.id}/accept/',
            {
                'assigned_rider_id': self.rider.id,
                'rider_assignment_type': 'measurement',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn('not enabled for measurement', response.data['message'].lower())
