"""Localized measurement_rows on order detail."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from apps.customization.services.shop_measurement_template import replace_shop_measurement_schema
from apps.orders.measurement_display import attach_field_label_snapshot, build_measurement_rows
from apps.orders.models import Order, OrderItem
from apps.orders.serializers import OrderItemSerializer
from apps.tailors.models import Fabric, ShopTailorPlusSubscription, TailorProfile

User = get_user_model()


@override_settings(SECURE_SSL_REDIRECT=False)
class OrderMeasurementRowsTest(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(username='cust_m', password='pass', role='USER')
        self.owner = User.objects.create_user(username='own_m', password='pass', role='TAILOR')
        self.shop = self.owner.tailor_profile
        self.shop.shop_name = 'Row Shop'
        self.shop.save(update_fields=['shop_name'])
        ShopTailorPlusSubscription.objects.create(
            shop=self.shop,
            status=ShopTailorPlusSubscription.STATUS_ACTIVE,
        )
        replace_shop_measurement_schema(
            shop=self.shop,
            fields_data=[
                {
                    'display_name': 'Special',
                    'display_name_ar': 'خاص',
                    'display_name_ur': 'خصوصی',
                    'display_order': 1,
                },
            ],
        )
        self.fabric = Fabric.objects.create(
            tailor=self.shop,
            name='F',
            price=Decimal('10'),
            stock=1,
        )
        self.order = Order.objects.create(
            customer=self.customer,
            tailor=self.owner,
            shop=self.shop,
            order_type='fabric_with_stitching',
            service_mode='walk_in',
            status='in_progress',
            payment_status='paid',
        )
        from apps.customization.services.shop_measurement_template import (
            resolve_measurement_template_for_shop,
        )

        resolved = resolve_measurement_template_for_shop(self.shop)
        custom_name = next(f['name'] for f in resolved['measurement_fields'] if f.get('is_custom'))
        self.custom_key = custom_name
        self.item = OrderItem.objects.create(
            order=self.order,
            fabric=self.fabric,
            quantity=1,
            unit_price=Decimal('10'),
            measurements={
                'waist': 40,
                custom_name: 2,
                'unit': 'cm',
                '_order': ['waist', custom_name],
            },
        )

    def test_build_rows_uses_field_map(self):
        rows = build_measurement_rows(
            self.item.measurements,
            field_map=__import__(
                'apps.orders.measurement_display', fromlist=['field_map_for_order']
            ).field_map_for_order(self.order),
            language='ar',
        )
        keys = [row['key'] for row in rows]
        self.assertEqual(keys, ['waist', self.custom_key])
        custom_row = next(r for r in rows if r['key'] == self.custom_key)
        self.assertEqual(custom_row['label'], 'خاص')

    def test_snapshot_overrides_after_template_change(self):
        stored = attach_field_label_snapshot(self.item.measurements, self.order)
        stored['_field_labels'][self.custom_key] = {
            'en': 'Frozen EN',
            'ar': 'Frozen AR',
            'ur': 'Frozen UR',
        }
        rows = build_measurement_rows(
            stored,
            field_map={},
            language='en',
        )
        custom_row = next(r for r in rows if r['key'] == self.custom_key)
        self.assertEqual(custom_row['label'], 'Frozen EN')

    def test_serializer_exposes_measurement_rows(self):
        from rest_framework.test import APIRequestFactory

        factory = APIRequestFactory()
        request = factory.get('/', HTTP_ACCEPT_LANGUAGE='ar')
        data = OrderItemSerializer(self.item, context={'request': request}).data
        self.assertIn('measurement_rows', data)
        self.assertNotIn('_field_labels', data['measurements'])
        self.assertNotIn('_order', data['measurements'])
        labels = [row['label'] for row in data['measurement_rows']]
        self.assertIn('خاص', labels)
