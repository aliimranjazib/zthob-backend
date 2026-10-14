"""Localized labels for shop measurement overlay."""

from django.test import TestCase

from apps.customization.measurement_labels import (
    localized_display_name,
    merge_label_columns_from_write,
    trilingual_labels,
)
from apps.customization.models import MeasurementField, MeasurementTemplate, ShopMeasurementField


class MeasurementLabelsTest(TestCase):
    def setUp(self):
        self.template = MeasurementTemplate.objects.create(
            name='t',
            display_name='EN template',
            display_name_ar='AR template',
        )
        self.global_field = MeasurementField.objects.create(
            template=self.template,
            name='waist',
            display_name='Waist EN',
            display_name_ar='Waist AR',
            display_name_ur='Waist UR',
        )

    def test_trilingual_merges_shop_override(self):
        shop_row = ShopMeasurementField(
            name='waist',
            display_name_ar='Shop AR',
        )
        en, ar, ur = trilingual_labels(
            global_field=self.global_field,
            shop_row=shop_row,
            storage_name='waist',
        )
        self.assertEqual(en, 'Waist EN')
        self.assertEqual(ar, 'Shop AR')
        self.assertEqual(ur, 'Waist UR')

    def test_merge_write_updates_only_request_language(self):
        existing = ShopMeasurementField(
            display_name='English',
            display_name_ar='Arabic',
            display_name_ur='Urdu',
        )
        merged = merge_label_columns_from_write(
            row={'display_name': 'New AR'},
            language='ar',
            existing=existing,
        )
        self.assertEqual(merged['display_name'], 'English')
        self.assertEqual(merged['display_name_ar'], 'New AR')
        self.assertEqual(merged['display_name_ur'], 'Urdu')

    def test_localized_display_name(self):
        label = localized_display_name(
            global_field=self.global_field,
            shop_row=None,
            language='ur',
            storage_name='waist',
        )
        self.assertEqual(label, 'Waist UR')
