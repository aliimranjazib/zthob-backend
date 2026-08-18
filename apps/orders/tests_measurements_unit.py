from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.test import APITestCase, APIClient

from apps.orders.measurement_utils import (
    get_measurement_unit,
    has_measurement_values,
    normalize_unit,
    ordered_measurement_keys,
    prepare_measurements_payload,
    public_measurements,
    resolve_measurement_recipient_items,
    with_measurement_order,
)
from apps.orders.models import Order, OrderItem
from apps.customers.models import FamilyMember
from apps.tailors.models import TailorEmployee, TailorProfile


User = get_user_model()


class MeasurementUtilsTest(TestCase):
    def test_normalize_unit_defaults_to_cm(self):
        self.assertEqual(normalize_unit(None), 'cm')
        self.assertEqual(normalize_unit(''), 'cm')
        self.assertEqual(normalize_unit('cm'), 'cm')

    def test_normalize_unit_accepts_inch_aliases(self):
        self.assertEqual(normalize_unit('inches'), 'inches')
        self.assertEqual(normalize_unit('in'), 'inches')
        self.assertEqual(normalize_unit('inch'), 'inches')

    def test_normalize_unit_rejects_unknown(self):
        with self.assertRaises(ValidationError):
            normalize_unit('meters')

    def test_prepare_measurements_payload_stores_unit_and_values(self):
        payload = prepare_measurements_payload(
            {'length': '56', 'shoulder': '22'},
            unit='inches',
            title='Wedding Thobe',
        )
        self.assertEqual(payload['unit'], 'inches')
        self.assertEqual(payload['title'], 'Wedding Thobe')
        self.assertEqual(payload['length'], 56)
        self.assertEqual(payload['shoulder'], 22)
        self.assertEqual(payload['_order'], ['length', 'shoulder'])

    def test_prepare_measurements_payload_defaults_unit_to_cm(self):
        payload = prepare_measurements_payload({'chest': 42})
        self.assertEqual(payload['unit'], 'cm')
        self.assertEqual(payload['chest'], 42)

    def test_has_measurement_values_ignores_metadata_only(self):
        self.assertFalse(has_measurement_values({'unit': 'cm'}))
        self.assertTrue(has_measurement_values({'unit': 'inches', 'length': 56}))

    def test_get_measurement_unit_falls_back_for_legacy_records(self):
        self.assertEqual(get_measurement_unit({'length': 42}), 'cm')
        self.assertEqual(get_measurement_unit({'unit': 'inches', 'length': 56}), 'inches')

    def test_with_measurement_order_keeps_payload_sequence(self):
        stored = with_measurement_order({'chest': 42, 'waist': 34, 'shoulder': 18})
        self.assertEqual(stored['_order'], ['chest', 'waist', 'shoulder'])

    def test_ordered_measurement_keys_uses_stored_order_when_keys_scrambled(self):
        scrambled = {
            'waist': 34,
            'shoulder': 18,
            'chest': 42,
            '_order': ['chest', 'waist', 'shoulder'],
        }
        self.assertEqual(
            ordered_measurement_keys(scrambled),
            ['chest', 'waist', 'shoulder'],
        )

    def test_public_measurements_hides_internal_order(self):
        stored = with_measurement_order({'chest': 42, 'waist': 34, 'unit': 'cm'})
        public = public_measurements(stored)
        self.assertNotIn('_order', public)
        self.assertEqual(public['chest'], 42)
        self.assertEqual(public['waist'], 34)
        self.assertEqual(public['unit'], 'cm')

    def test_has_measurement_values_ignores_order_metadata(self):
        self.assertFalse(has_measurement_values({'_order': ['chest'], 'unit': 'cm'}))


@override_settings(
    SECURE_SSL_REDIRECT=False,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}},
)
class RecordMeasurementsUnitActionTest(APITestCase):
    def setUp(self):
        self.customer = User.objects.create_user(
            username='measure_unit_customer',
            password='testpass123',
            role='USER',
        )
        self.owner = User.objects.create_user(
            username='measure_unit_owner',
            password='testpass123',
            role='TAILOR',
        )
        self.owner_profile, _ = TailorProfile.objects.get_or_create(
            user=self.owner,
            defaults={'shop_name': 'Unit Test Shop', 'shop_status': True},
        )
        self.employee_user = User.objects.create_user(
            username='measure_unit_employee',
            password='testpass123',
            role='TAILOR',
        )
        self.employee = TailorEmployee.objects.create(
            tailor=self.owner_profile,
            user=self.employee_user,
            roles=['manager'],
            can_manage_orders=True,
            is_active=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.employee_user)

    def _create_walk_in_order(self):
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

    def test_record_measurements_without_unit_defaults_to_cm(self):
        order = self._create_walk_in_order()

        response = self.client.post(
            f'/api/orders/{order.id}/action/',
            data={
                'action': 'record_measurements',
                'role': 'TAILOR',
                'data': {
                    'measurements': {'length': 142, 'shoulder': 48},
                    'family_member': None,
                },
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        item = order.order_items.first()
        self.assertEqual(item.measurements['unit'], 'cm')
        self.assertEqual(item.measurements['length'], 142)
        self.assertEqual(item.measurements['_order'], ['length', 'shoulder'])
        self.assertTrue(order.all_items_have_measurements)

    def test_record_measurements_with_inches_unit(self):
        order = self._create_walk_in_order()

        response = self.client.post(
            f'/api/orders/{order.id}/action/',
            data={
                'action': 'record_measurements',
                'role': 'TAILOR',
                'data': {
                    'unit': 'inches',
                    'measurements': {
                        'length': '56',
                        'shoulder': '22',
                        'chest_front': '44',
                    },
                    'family_member': None,
                },
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        item = order.order_items.first()
        self.assertEqual(item.measurements['unit'], 'inches')
        self.assertEqual(item.measurements['length'], 56)
        self.assertEqual(item.measurements['shoulder'], 22)
        self.assertTrue(order.all_items_have_measurements)

    def test_record_measurements_rejects_invalid_unit(self):
        order = self._create_walk_in_order()

        response = self.client.post(
            f'/api/orders/{order.id}/action/',
            data={
                'action': 'record_measurements',
                'role': 'TAILOR',
                'data': {
                    'unit': 'meters',
                    'measurements': {'length': 140},
                    'family_member': None,
                },
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        order.refresh_from_db()
        self.assertFalse(order.all_items_have_measurements)

    def test_record_measurements_falls_back_when_stale_family_member_on_self_order(self):
        order = self._create_walk_in_order()
        stale_member = FamilyMember.objects.create(
            user=self.customer,
            name='Previous Recipient',
            relationship='son',
        )

        response = self.client.post(
            f'/api/orders/{order.id}/action/',
            data={
                'action': 'record_measurements',
                'role': 'TAILOR',
                'data': {
                    'measurements': {'chest': 40, 'length': 58},
                    'family_member': stale_member.id,
                },
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        order.refresh_from_db()
        item = order.order_items.get()
        self.assertEqual(item.measurements['chest'], 40)
        self.assertTrue(order.all_items_have_measurements)

    def test_record_measurements_falls_back_when_family_item_submitted_as_self(self):
        family_member = FamilyMember.objects.create(
            user=self.customer,
            name='Ali',
            relationship='brother',
        )
        order = self._create_walk_in_order()
        order.order_items.update(family_member=family_member)

        response = self.client.post(
            f'/api/orders/{order.id}/action/',
            data={
                'action': 'record_measurements',
                'role': 'TAILOR',
                'data': {
                    'measurements': {'chest': 42, 'length': 60},
                    'family_member': None,
                },
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        item = order.order_items.get()
        self.assertEqual(item.measurements['chest'], 42)

    def test_record_measurements_does_not_fallback_on_mixed_recipients(self):
        family_member = FamilyMember.objects.create(
            user=self.customer,
            name='Ali',
            relationship='brother',
        )
        other_member = FamilyMember.objects.create(
            user=self.customer,
            name='Omar',
            relationship='son',
        )
        order = self._create_walk_in_order()
        order.order_items.update(family_member=family_member)
        OrderItem.objects.create(
            order=order,
            quantity=1,
            unit_price=Decimal('100.00'),
            family_member=other_member,
        )

        response = self.client.post(
            f'/api/orders/{order.id}/action/',
            data={
                'action': 'record_measurements',
                'role': 'TAILOR',
                'data': {
                    'measurements': {'chest': 40},
                    'family_member': None,
                },
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('No order items found for the selected recipient', str(response.data))
        self.assertFalse(
            any(has_measurement_values(item.measurements) for item in order.order_items.all())
        )


class ResolveMeasurementRecipientItemsTest(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(
            username='recipient_match_customer',
            password='testpass123',
            role='USER',
        )
        self.tailor = User.objects.create_user(
            username='recipient_match_tailor',
            password='testpass123',
            role='TAILOR',
        )
        self.order = Order.objects.create(
            customer=self.customer,
            tailor=self.tailor,
            order_type='stitching_only',
            service_mode='walk_in',
            payment_method='cod',
            payment_status='paid',
            status='confirmed',
            tailor_status='accepted',
            stitching_price=Decimal('80.00'),
            total_amount=Decimal('80.00'),
        )

    def test_exact_family_member_match_wins(self):
        member = FamilyMember.objects.create(user=self.customer, name='Ali')
        other = FamilyMember.objects.create(user=self.customer, name='Omar')
        matched = OrderItem.objects.create(
            order=self.order, quantity=1, unit_price=Decimal('0.00'), family_member=member,
        )
        OrderItem.objects.create(
            order=self.order, quantity=1, unit_price=Decimal('0.00'), family_member=other,
        )

        items = resolve_measurement_recipient_items(self.order, member.id)
        self.assertEqual(list(items.values_list('id', flat=True)), [matched.id])

    def test_single_recipient_fallback_for_stale_id(self):
        OrderItem.objects.create(
            order=self.order, quantity=1, unit_price=Decimal('0.00'),
        )
        stale = FamilyMember.objects.create(user=self.customer, name='Stale')

        items = resolve_measurement_recipient_items(self.order, stale.id)
        self.assertEqual(items.count(), 1)
