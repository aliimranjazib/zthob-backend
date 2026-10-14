"""Shop-scoped measurement template overlay (Tailor Plus)."""

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from apps.customization.models import (
    MeasurementField,
    MeasurementTemplate,
    ShopMeasurementField,
    ShopMeasurementSchema,
)
from apps.customization.services.shop_measurement_template import (
    replace_shop_measurement_schema,
    reset_shop_measurement_schema,
    resolve_measurement_template_for_shop,
    shop_has_custom_measurement_schema,
)
from apps.tailors.models import ShopTailorPlusSubscription, TailorProfile
from apps.tailors.services.shop_plus import TailorPlusLimitError

User = get_user_model()


@override_settings(SECURE_SSL_REDIRECT=False)
class ShopMeasurementTemplateTest(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='meas_owner', password='pass', role='TAILOR')
        self.shop = self.owner.tailor_profile
        self.shop.shop_name = 'Meas Shop'
        self.shop.shop_status = True
        self.shop.save(update_fields=['shop_name', 'shop_status'])
        self.template, _ = MeasurementTemplate.objects.get_or_create(
            name='measurements_template',
            defaults={
                'display_name': 'Thobe Measurements',
                'display_name_ar': 'Thobe AR',
                'display_name_ur': 'Thobe UR',
                'default_unit': 'cm',
                'is_active': True,
            },
        )
        self.global_field, _ = MeasurementField.objects.get_or_create(
            template=self.template,
            name='chest',
            defaults={
                'display_name': 'Chest',
                'display_name_ar': 'Chest AR',
                'display_name_ur': 'Chest UR',
                'field_type': 'decimal',
                'is_active': True,
                'display_order': 1,
            },
        )

    def _activate_plus(self):
        ShopTailorPlusSubscription.objects.create(
            shop=self.shop,
            status=ShopTailorPlusSubscription.STATUS_ACTIVE,
        )

    def test_free_shop_returns_global_source(self):
        payload = resolve_measurement_template_for_shop(self.shop)
        self.assertEqual(payload['source'], 'global')
        self.assertFalse(payload['is_editable'])
        names = [f['name'] for f in payload['measurement_fields']]
        self.assertIn('chest', names)

    def test_plus_hide_global_field(self):
        self._activate_plus()
        replace_shop_measurement_schema(
            shop=self.shop,
            fields_data=[
                {
                    'global_field_id': self.global_field.id,
                    'is_visible': False,
                    'display_order': 1,
                }
            ],
        )
        payload = resolve_measurement_template_for_shop(self.shop)
        self.assertEqual(payload['source'], 'shop_custom')
        names = [f['name'] for f in payload['measurement_fields']]
        self.assertNotIn('chest', names)
        self.assertTrue(shop_has_custom_measurement_schema(self.shop))

    def test_plus_add_custom_field(self):
        self._activate_plus()
        replace_shop_measurement_schema(
            shop=self.shop,
            fields_data=[
                {
                    'global_field_id': self.global_field.id,
                    'is_visible': True,
                    'display_order': 1,
                },
                {
                    'is_visible': True,
                    'display_name': 'خاص',
                    'display_order': 2,
                },
            ],
            language='ar',
        )
        from rest_framework.test import APIRequestFactory

        factory = APIRequestFactory()
        request = factory.get('/', HTTP_ACCEPT_LANGUAGE='ar')
        payload = resolve_measurement_template_for_shop(self.shop, request=request)
        names = [f['name'] for f in payload['measurement_fields']]
        self.assertIn('chest', names)
        custom = next(f for f in payload['measurement_fields'] if f.get('is_custom'))
        self.assertTrue(custom['name'].startswith('sf_'))
        self.assertEqual(custom['display_name'], 'خاص')
        self.assertNotIn('display_name_ar', custom)
        row = ShopMeasurementField.objects.get(id=custom['id'])
        self.assertEqual(row.display_name_ar, 'خاص')

    def test_custom_field_key_stable_on_resave(self):
        self._activate_plus()
        replace_shop_measurement_schema(
            shop=self.shop,
            fields_data=[
                {
                    'global_field_id': self.global_field.id,
                    'is_visible': True,
                    'display_order': 1,
                },
                {
                    'display_name': 'First label',
                    'display_order': 2,
                },
            ],
            language='en',
        )
        first = resolve_measurement_template_for_shop(self.shop)
        custom = next(f for f in first['measurement_fields'] if f.get('is_custom'))
        field_id = custom['id']
        storage_name = custom['name']

        replace_shop_measurement_schema(
            shop=self.shop,
            fields_data=[
                {
                    'global_field_id': self.global_field.id,
                    'is_visible': True,
                    'display_order': 1,
                },
                {
                    'id': field_id,
                    'display_name': 'ب',
                    'display_order': 2,
                },
            ],
            language='ar',
        )
        second = resolve_measurement_template_for_shop(self.shop)
        custom2 = next(f for f in second['measurement_fields'] if f.get('is_custom'))
        self.assertEqual(custom2['name'], storage_name)
        self.assertEqual(custom2['display_name'], 'First label')
        row = ShopMeasurementField.objects.get(id=field_id)
        self.assertEqual(row.display_name, 'First label')
        self.assertEqual(row.display_name_ar, 'ب')

    def test_non_plus_cannot_save(self):
        with self.assertRaises(TailorPlusLimitError):
            replace_shop_measurement_schema(
                shop=self.shop,
                fields_data=[{'global_field_id': self.global_field.id}],
            )

    def test_reset_removes_custom_schema(self):
        self._activate_plus()
        replace_shop_measurement_schema(
            shop=self.shop,
            fields_data=[{'global_field_id': self.global_field.id, 'is_visible': False}],
        )
        reset_shop_measurement_schema(shop=self.shop)
        self.assertFalse(ShopMeasurementSchema.objects.filter(shop=self.shop).exists())
        payload = resolve_measurement_template_for_shop(self.shop)
        self.assertEqual(payload['source'], 'global')
