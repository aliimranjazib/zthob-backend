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
    prepare_measurements_payload,
)
from apps.orders.models import Order, OrderItem
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
