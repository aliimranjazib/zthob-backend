from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.customers.models import CustomerProfile, FamilyMember
from apps.orders.models import Order, OrderItem
from apps.tailors.models import TailorProfile

User = get_user_model()

CUSTOMER_MEASUREMENTS = {'chest': 42, 'unit': 'cm'}
FAMILY_MEASUREMENTS = {'chest': 38, 'unit': 'cm'}
WALK_IN_MEASUREMENTS = {'length': 140, 'shoulder': 46, 'unit': 'cm'}


@override_settings(SECURE_SSL_REDIRECT=False)
class CustomerMeasurementsAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = User.objects.create_user(
            username='measurements_customer',
            password='testpass123',
            role='USER',
        )
        CustomerProfile.objects.get_or_create(user=self.customer)
        self.tailor = User.objects.create_user(
            username='measurements_tailor',
            password='testpass123',
            role='TAILOR',
        )
        self.tailor_profile, _ = TailorProfile.objects.get_or_create(
            user=self.tailor,
            defaults={'shop_name': 'Measurements Tailor', 'shop_status': True},
        )
        self.family_member = FamilyMember.objects.create(
            user=self.customer,
            name='Ahmed Jr',
            relationship='son',
            gender='male',
        )
        self.client.force_authenticate(user=self.customer)

    def _recipient(self, recipient_type, recipient_id=None):
        response = self.client.get('/api/customers/measurements/')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        for recipient in response.data['data']['recipients']:
            if recipient['recipient_type'] != recipient_type:
                continue
            if recipient_id is not None and recipient['recipient_id'] != recipient_id:
                continue
            return recipient
        self.fail(f'Recipient {recipient_type} {recipient_id} not found in {response.data}')

    def _create_delivered_rider_order(self, *, family_member=None, measurements=None):
        taken_at = timezone.now() - timezone.timedelta(days=1)
        order = Order.objects.create(
            customer=self.customer,
            tailor=self.tailor,
            order_type='fabric_with_stitching',
            service_mode='home_delivery',
            status='delivered',
            tailor_status='stitched',
            rider_status='delivered',
            payment_status='paid',
            total_amount=Decimal('100.00'),
            paid_amount=Decimal('100.00'),
            remaining_amount=Decimal('0.00'),
            rider_measurements=measurements or CUSTOMER_MEASUREMENTS,
            measurement_taken_at=taken_at,
        )
        OrderItem.objects.create(
            order=order,
            quantity=1,
            unit_price=Decimal('100.00'),
            total_price=Decimal('100.00'),
            family_member=family_member,
            measurements=measurements or CUSTOMER_MEASUREMENTS,
        )
        return order

    def test_delivered_rider_order_appears_in_order_history(self):
        order = self._create_delivered_rider_order()

        recipient = self._recipient('customer', self.customer.id)
        self.assertEqual(len(recipient['order_history']), 1)
        history_entry = recipient['order_history'][0]
        self.assertEqual(history_entry['order_id'], order.id)
        self.assertEqual(history_entry['order_status'], 'delivered')
        self.assertEqual(history_entry['rider_status'], 'delivered')
        self.assertEqual(history_entry['measurements']['chest'], 42)

    def test_delivered_rider_order_family_member_in_history(self):
        order = self._create_delivered_rider_order(
            family_member=self.family_member,
            measurements=FAMILY_MEASUREMENTS,
        )

        recipient = self._recipient('family_member', self.family_member.id)
        self.assertEqual(len(recipient['order_history']), 1)
        history_entry = recipient['order_history'][0]
        self.assertEqual(history_entry['order_id'], order.id)
        self.assertEqual(history_entry['measurements']['chest'], 38)

    def test_walk_in_tailor_order_appears_in_history(self):
        taken_at = timezone.now() - timezone.timedelta(hours=2)
        order = Order.objects.create(
            customer=self.customer,
            tailor=self.tailor,
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
        family_order = Order.objects.create(
            customer=self.customer,
            tailor=self.tailor,
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
            order=family_order,
            quantity=1,
            unit_price=Decimal('100.00'),
            total_price=Decimal('100.00'),
            family_member=self.family_member,
            measurements=FAMILY_MEASUREMENTS,
        )

        customer_recipient = self._recipient('customer', self.customer.id)
        self.assertEqual(len(customer_recipient['order_history']), 1)
        self.assertEqual(
            customer_recipient['order_history'][0]['measurements']['length'],
            140,
        )

        family_recipient = self._recipient('family_member', self.family_member.id)
        self.assertEqual(len(family_recipient['order_history']), 1)
        self.assertEqual(
            family_recipient['order_history'][0]['measurements']['chest'],
            38,
        )

    def test_current_measurements_fallback_from_latest_order(self):
        profile = self.customer.customer_profile
        profile.measurements = None
        profile.save(update_fields=['measurements'])

        newer = timezone.now()
        older = newer - timezone.timedelta(days=3)
        older_order = Order.objects.create(
            customer=self.customer,
            tailor=self.tailor,
            order_type='fabric_with_stitching',
            service_mode='home_delivery',
            status='delivered',
            rider_status='delivered',
            payment_status='paid',
            total_amount=Decimal('100.00'),
            paid_amount=Decimal('100.00'),
            remaining_amount=Decimal('0.00'),
            measurement_taken_at=older,
        )
        OrderItem.objects.create(
            order=older_order,
            quantity=1,
            unit_price=Decimal('100.00'),
            total_price=Decimal('100.00'),
            measurements={'chest': 40, 'unit': 'cm'},
        )

        latest_order = Order.objects.create(
            customer=self.customer,
            tailor=self.tailor,
            order_type='fabric_with_stitching',
            service_mode='home_delivery',
            status='delivered',
            rider_status='delivered',
            payment_status='paid',
            total_amount=Decimal('100.00'),
            paid_amount=Decimal('100.00'),
            remaining_amount=Decimal('0.00'),
            measurement_taken_at=newer,
        )
        OrderItem.objects.create(
            order=latest_order,
            quantity=1,
            unit_price=Decimal('100.00'),
            total_price=Decimal('100.00'),
            measurements=CUSTOMER_MEASUREMENTS,
        )

        recipient = self._recipient('customer', self.customer.id)
        self.assertEqual(recipient['current_measurements']['chest'], 42)
        self.assertEqual(
            recipient['current_measurements_note'],
            'Latest order measurements',
        )

    def test_family_member_measurements_endpoint_includes_delivered(self):
        order = self._create_delivered_rider_order(
            family_member=self.family_member,
            measurements=FAMILY_MEASUREMENTS,
        )
        self.family_member.measurements = None
        self.family_member.save(update_fields=['measurements'])

        response = self.client.get(
            f'/api/customers/family/{self.family_member.id}/measurements/'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        order_measurements = response.data['data']['order_measurements']
        self.assertEqual(len(order_measurements), 1)
        self.assertEqual(order_measurements[0]['order_id'], order.id)
        self.assertEqual(order_measurements[0]['order_status'], 'delivered')
        self.assertEqual(order_measurements[0]['rider_status'], 'delivered')
        self.assertEqual(order_measurements[0]['measurements']['chest'], 38)
