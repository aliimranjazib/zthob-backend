from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.customers.models import Address
from apps.deliveries.models import DeliveryTracking
from apps.deliveries.services import DeliveryTrackingService
from apps.orders.models import Order, OrderItem
from apps.riders.models import RiderProfile, RiderProfileReview
from apps.tailors.models import TailorProfile

User = get_user_model()


@override_settings(
    SECURE_SSL_REDIRECT=False,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}},
)
class CustomerTrackingRiderAssignmentTest(APITestCase):
    def setUp(self):
        self.customer = User.objects.create_user(
            username='tracking_customer',
            password='testpass123',
            role='USER',
        )
        self.tailor = User.objects.create_user(
            username='tracking_tailor',
            password='testpass123',
            role='TAILOR',
        )
        TailorProfile.objects.get_or_create(
            user=self.tailor,
            defaults={'shop_name': 'Tracking Tailor', 'shop_status': True},
        )
        self.measurement_rider = self._create_rider('tracking_measurement_rider')
        self.delivery_rider = self._create_rider('tracking_delivery_rider')
        self.reassigned_delivery_rider = self._create_rider('tracking_delivery_rider_2')
        self.address = Address.objects.create(
            user=self.customer,
            street='1 Tracking St',
            city='Riyadh',
            country='Saudi Arabia',
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.customer)

    def _create_rider(self, username):
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

    def _create_stitching_order(self, *, measurements=None):
        order = Order.objects.create(
            customer=self.customer,
            tailor=self.tailor,
            order_type='fabric_with_stitching',
            service_mode='home_delivery',
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
            quantity=1,
            unit_price=Decimal('100.00'),
            measurements=measurements or {'chest': 42, 'unit': 'cm'},
        )
        return order

    def _tracking_url(self, order_id):
        return f'/api/deliveries/customer/orders/{order_id}/tracking/'

    def test_measurement_rider_preserved_after_delivery_assignment(self):
        order = self._create_stitching_order()
        order.measurement_rider = self.measurement_rider
        order.rider = self.measurement_rider
        order.assigned_rider = self.measurement_rider
        order.save()
        DeliveryTrackingService.create_tracking_for_order(order)

        order.delivery_rider = self.delivery_rider
        order.rider = self.delivery_rider
        order.assigned_rider = self.delivery_rider
        order.status = 'ready_for_delivery'
        order.rider_status = 'none'
        order.save()

        response = self.client.get(self._tracking_url(order.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        data = response.data['data']
        self.assertEqual(data['measurement_rider_info']['id'], self.measurement_rider.id)
        self.assertEqual(data['delivery_rider_info']['id'], self.delivery_rider.id)
        self.assertEqual(data['active_rider_info']['id'], self.delivery_rider.id)
        self.assertEqual(data['rider_name'], 'tracking_delivery_rider')

        tracking = DeliveryTracking.objects.get(order=order)
        self.assertEqual(tracking.rider_id, self.delivery_rider.id)

    def test_delivery_rider_reassignment_updates_active_tracking_rider(self):
        order = self._create_stitching_order()
        order.measurement_rider = self.measurement_rider
        order.delivery_rider = self.delivery_rider
        order.rider = self.delivery_rider
        order.assigned_rider = self.delivery_rider
        order.status = 'ready_for_delivery'
        order.tailor_status = 'stitched'
        order.save()
        DeliveryTrackingService.create_tracking_for_order(order)

        order.delivery_rider = self.reassigned_delivery_rider
        order.rider = self.reassigned_delivery_rider
        order.assigned_rider = self.reassigned_delivery_rider
        order.save()

        response = self.client.get(self._tracking_url(order.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        data = response.data['data']
        self.assertEqual(data['measurement_rider_info']['id'], self.measurement_rider.id)
        self.assertEqual(data['delivery_rider_info']['id'], self.reassigned_delivery_rider.id)
        self.assertEqual(data['active_rider_info']['id'], self.reassigned_delivery_rider.id)

        tracking = DeliveryTracking.objects.get(order=order)
        self.assertEqual(tracking.rider_id, self.reassigned_delivery_rider.id)

    def test_measurement_phase_uses_measurement_rider_for_active_tracking(self):
        order = self._create_stitching_order(measurements={})
        order.measurement_rider = self.measurement_rider
        order.rider = self.measurement_rider
        order.assigned_rider = self.measurement_rider
        order.rider_status = 'accepted'
        order.save()
        DeliveryTrackingService.create_tracking_for_order(order)

        response = self.client.get(self._tracking_url(order.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        data = response.data['data']
        self.assertEqual(data['measurement_rider_info']['id'], self.measurement_rider.id)
        self.assertIsNone(data['delivery_rider_info'])
        self.assertEqual(data['active_rider_info']['id'], self.measurement_rider.id)
