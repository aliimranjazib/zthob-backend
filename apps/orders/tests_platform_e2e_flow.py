"""
End-to-end platform flow test.

Run before releases or after cross-app changes:

    uv run python manage.py test apps.orders.tests_platform_e2e_flow -v 2

Covers customer (POS + app), tailor, and rider apps through home-delivery delivery.
"""
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.core.services import PhoneVerificationService
from apps.customers.models import Address, CustomerProfile
from apps.orders.models import Order
from apps.riders.models import RiderProfile, RiderProfileReview
from apps.tailors.models import Fabric, FabricCategory, TailorProfile


User = get_user_model()


@override_settings(
    SECURE_SSL_REDIRECT=False,
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    },
)
class PlatformEndToEndFlowTest(TestCase):
    """
    Single happy-path test across customer, tailor, and rider APIs.

    Flow:
      1. Tailor creates POS customer
      2. Phone login resolves the same customer account
      3. Customer places COD home-delivery stitching order
      4. Tailor accepts and assigns measurement rider
      5. Rider takes measurements
      6. Tailor stitches and marks ready with delivery rider
      7. Rider delivers (collects COD, marks delivered)
      8. Customer, tailor, and rider views all reflect final state
    """

    POS_PHONE = '966500000777'
    LOCAL_PHONE = '0500000777'

    def setUp(self):
        patch(
            'apps.notifications.tasks.send_order_status_notification_task.delay'
        ).start()
        patch(
            'apps.notifications.tasks.send_rider_status_notification_task.delay'
        ).start()
        patch(
            'apps.notifications.tasks.send_tailor_status_notification_task.delay'
        ).start()
        patch(
            'apps.notifications.services.NotificationService.send_new_order_broadcast'
        ).start()
        patch(
            'apps.notifications.services.NotificationService.send_notification'
        ).start()
        patch('apps.customers.services.welcome_sms.queue_customer_welcome_sms').start()
        self.addCleanup(patch.stopall)

        self.tailor_user = User.objects.create_user(
            username='e2e_tailor',
            phone='+966500000111',
            role='TAILOR',
        )
        self.tailor_profile, _ = TailorProfile.objects.get_or_create(user=self.tailor_user)
        self.tailor_profile.shop_name = 'E2E Tailor Shop'
        self.tailor_profile.shop_status = True
        self.tailor_profile.save(update_fields=['shop_name', 'shop_status'])

        self.fabric_category = FabricCategory.objects.create(name='E2E Cotton', slug='e2e-cotton')
        self.fabric = Fabric.objects.create(
            tailor=self.tailor_profile,
            name='E2E Fabric',
            price=Decimal('120.00'),
            stock=10,
            is_active=True,
            category=self.fabric_category,
        )

        self.measurement_rider = self._create_approved_rider('e2e_measurement_rider', '+966500000222')
        self.delivery_rider = self._create_approved_rider('e2e_delivery_rider', '+966500000333')

        self.tailor_client = APIClient()
        self.tailor_client.force_authenticate(user=self.tailor_user)
        self.customer_client = APIClient()
        self.measurement_rider_client = APIClient()
        self.measurement_rider_client.force_authenticate(user=self.measurement_rider)
        self.delivery_rider_client = APIClient()
        self.delivery_rider_client.force_authenticate(user=self.delivery_rider)

    def _create_approved_rider(self, username, phone):
        rider = User.objects.create_user(username=username, phone=phone, role='RIDER')
        profile, _ = RiderProfile.objects.get_or_create(user=rider)
        profile.full_name = username
        profile.vehicle_type = 'bike'
        profile.rating = Decimal('4.80')
        profile.is_available = True
        profile.save(update_fields=['full_name', 'vehicle_type', 'rating', 'is_available'])
        review, _ = RiderProfileReview.objects.get_or_create(profile=profile)
        review.review_status = 'approved'
        review.save(update_fields=['review_status'])
        return rider

    def _post_action(self, client, order_id, action, role, data=None):
        payload = {'action': action, 'role': role}
        if data is not None:
            payload['data'] = data
        return client.post(f'/api/orders/{order_id}/action/', payload, format='json')

    def test_full_platform_home_delivery_cod_flow(self):
        # ── 1. Tailor creates POS customer ───────────────────────────────────
        create_customer_response = self.tailor_client.post(
            '/api/tailors/pos/customers/create/',
            {'phone': self.POS_PHONE, 'name': 'E2E Platform Customer'},
            format='json',
        )
        self.assertEqual(create_customer_response.status_code, status.HTTP_201_CREATED, create_customer_response.data)
        customer_id = create_customer_response.data['data']['id']
        customer = User.objects.get(id=customer_id)
        self.assertEqual(customer.phone, self.LOCAL_PHONE)
        self.assertTrue(CustomerProfile.objects.filter(user=customer, pos_created_by=self.tailor_user).exists())

        # ── 2. Phone login resolves same account (no duplicate user) ─────────
        login_user = PhoneVerificationService._find_or_create_user(self.LOCAL_PHONE)
        self.assertEqual(login_user.id, customer.id)

        address = Address.objects.create(
            user=customer,
            street='E2E Delivery Street',
            city='Riyadh',
            country='Saudi Arabia',
            latitude=Decimal('24.713600'),
            longitude=Decimal('46.675300'),
        )
        self.customer_client.force_authenticate(user=customer)

        # ── 3. Customer creates COD home-delivery order ──────────────────────
        create_order_response = self.customer_client.post(
            '/api/orders/create/',
            {
                'tailor': self.tailor_user.id,
                'order_type': 'fabric_with_stitching',
                'service_mode': 'home_delivery',
                'payment_method': 'cod',
                'delivery_address': address.id,
                'items': [
                    {
                        'fabric': self.fabric.id,
                        'quantity': 1,
                        'measurements': {},
                        'custom_instructions': 'E2E platform test order',
                    }
                ],
            },
            format='json',
        )
        self.assertEqual(create_order_response.status_code, status.HTTP_201_CREATED, create_order_response.data)
        order_id = create_order_response.data['data']['id']
        order = Order.objects.get(id=order_id)
        self.assertEqual(order.customer_id, customer.id)
        self.assertEqual(order.tailor_id, self.tailor_user.id)
        self.assertEqual(order.status, 'pending')
        self.assertEqual(order.payment_method, 'cod')
        self.assertEqual(order.payment_status, 'pending')

        # ── 4. Customer sees the order in my-orders ──────────────────────────
        my_orders_response = self.customer_client.get('/api/orders/customer/my-orders/')
        self.assertEqual(my_orders_response.status_code, status.HTTP_200_OK, my_orders_response.data)
        my_order_ids = [item['id'] for item in my_orders_response.data['data']]
        self.assertIn(order_id, my_order_ids)

        order_detail_response = self.customer_client.get(f'/api/orders/{order_id}/')
        self.assertEqual(order_detail_response.status_code, status.HTTP_200_OK, order_detail_response.data)
        self.assertEqual(
            order_detail_response.data['data']['items'][0]['custom_instructions'],
            'E2E platform test order',
        )

        # ── 5. Tailor accepts and assigns measurement rider ────────────────
        accept_response = self._post_action(
            self.tailor_client,
            order_id,
            'accept_order',
            'TAILOR',
            {
                'assigned_rider_id': self.measurement_rider.id,
                'rider_assignment_type': 'measurement',
            },
        )
        self.assertEqual(accept_response.status_code, status.HTTP_200_OK, accept_response.data)
        order.refresh_from_db()
        self.assertEqual(order.status, 'confirmed')
        self.assertEqual(order.tailor_status, 'accepted')
        self.assertEqual(order.measurement_rider_id, self.measurement_rider.id)

        tailor_available_response = self.tailor_client.get('/api/orders/tailor/available-orders/')
        self.assertEqual(tailor_available_response.status_code, status.HTTP_200_OK)
        self.assertIn(order_id, [item['id'] for item in tailor_available_response.data['data']])

        # ── 6. Measurement rider workflow ──────────────────────────────────
        for action in ('accept_order', 'start_measuring'):
            response = self._post_action(self.measurement_rider_client, order_id, action, 'RIDER')
            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        record_measurements_response = self._post_action(
            self.measurement_rider_client,
            order_id,
            'record_measurements',
            'RIDER',
            {'measurements': {'chest': 104, 'length': 146}},
        )
        self.assertEqual(record_measurements_response.status_code, status.HTTP_200_OK, record_measurements_response.data)
        order.refresh_from_db()
        self.assertEqual(order.rider_status, 'measurement_taken')
        item_measurements = order.order_items.get().measurements
        self.assertEqual(item_measurements.get('chest'), 104)
        self.assertEqual(item_measurements.get('length'), 146)

        # ── 7. Tailor stitching workflow ───────────────────────────────────
        stitching_date = (timezone.now().date() + timedelta(days=7)).isoformat()
        start_stitching_response = self._post_action(
            self.tailor_client,
            order_id,
            'start_stitching',
            'TAILOR',
            {'stitching_completion_date': stitching_date},
        )
        self.assertEqual(start_stitching_response.status_code, status.HTTP_200_OK, start_stitching_response.data)

        finish_stitching_response = self._post_action(
            self.tailor_client, order_id, 'finish_stitching', 'TAILOR'
        )
        self.assertEqual(finish_stitching_response.status_code, status.HTTP_200_OK, finish_stitching_response.data)

        mark_ready_response = self._post_action(
            self.tailor_client,
            order_id,
            'mark_ready',
            'TAILOR',
            {'assigned_rider_id': self.delivery_rider.id},
        )
        self.assertEqual(mark_ready_response.status_code, status.HTTP_200_OK, mark_ready_response.data)
        order.refresh_from_db()
        self.assertEqual(order.status, 'ready_for_delivery')
        self.assertEqual(order.delivery_rider_id, self.delivery_rider.id)

        # ── 8. Delivery rider workflow + COD collection ────────────────────
        rider_my_orders_response = self.delivery_rider_client.get('/api/riders/orders/my-orders/')
        self.assertEqual(rider_my_orders_response.status_code, status.HTTP_200_OK, rider_my_orders_response.data)
        self.assertIn(order_id, [item['id'] for item in rider_my_orders_response.data['data']])

        for action in ('accept_order', 'pickup_order', 'start_delivery'):
            response = self._post_action(self.delivery_rider_client, order_id, action, 'RIDER')
            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        order.refresh_from_db()
        self.assertTrue(order.has_remaining_balance)

        collect_cash_response = self._post_action(
            self.delivery_rider_client, order_id, 'collect_cash_payment', 'RIDER', {}
        )
        self.assertEqual(collect_cash_response.status_code, status.HTTP_200_OK, collect_cash_response.data)
        order.refresh_from_db()
        self.assertEqual(order.payment_status, 'paid')
        self.assertFalse(order.has_remaining_balance)

        delivered_response = self._post_action(
            self.delivery_rider_client, order_id, 'mark_delivered', 'RIDER'
        )
        self.assertEqual(delivered_response.status_code, status.HTTP_200_OK, delivered_response.data)

        # ── 9. Final state across all apps ─────────────────────────────────
        order.refresh_from_db()
        self.assertEqual(order.status, 'delivered')
        self.assertEqual(order.rider_status, 'delivered')
        self.assertEqual(order.measurement_rider_id, self.measurement_rider.id)
        self.assertEqual(order.delivery_rider_id, self.delivery_rider.id)
        self.assertEqual(order.rider_id, self.delivery_rider.id)

        final_customer_orders = self.customer_client.get('/api/orders/customer/my-orders/')
        self.assertEqual(final_customer_orders.status_code, status.HTTP_200_OK)
        delivered_entry = next(item for item in final_customer_orders.data['data'] if item['id'] == order_id)
        self.assertEqual(delivered_entry['status'], 'delivered')
        self.assertEqual(delivered_entry['payment_status'], 'paid')

        final_customer_detail = self.customer_client.get(f'/api/orders/{order_id}/')
        self.assertEqual(final_customer_detail.status_code, status.HTTP_200_OK)
        self.assertEqual(final_customer_detail.data['data']['status'], 'delivered')

        tracking_response = self.customer_client.get(
            f'/api/deliveries/customer/orders/{order_id}/tracking/'
        )
        self.assertEqual(tracking_response.status_code, status.HTTP_200_OK, tracking_response.data)

        tailor_available_response = self.tailor_client.get('/api/orders/tailor/available-orders/')
        self.assertEqual(tailor_available_response.status_code, status.HTTP_200_OK)
        available_order_ids = [item['id'] for item in tailor_available_response.data['data']]
        self.assertNotIn(order_id, available_order_ids)

        pos_customer_orders_response = self.tailor_client.get(
            f'/api/tailors/pos/customers/{customer.id}/orders/'
        )
        self.assertEqual(pos_customer_orders_response.status_code, status.HTTP_200_OK, pos_customer_orders_response.data)
        self.assertIn(order_id, [item['id'] for item in pos_customer_orders_response.data['data']])
