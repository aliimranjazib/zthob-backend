from django.test import TestCase

from apps.customization.models import MeasurementField, MeasurementTemplate
from apps.documents.measurement_config import (
    DEFAULT_APP_PDF_GRID,
    build_pdf_field_map,
    get_pdf_measurement_template,
)
from apps.documents.measurement_grid import build_measurement_grid_cells
from apps.documents.service import generate_order_html

LEGACY_ORDER = {
    'armpit': 17,
    'chest_girth': 6,
    'chest_lower': 8,
    'chest_upper': 7,
    'cufflink': 15,
    'flipped_collar': 12,
    'hem': 3,
    'hips': 10,
    'lower_width': 11,
    'shoulder_back': 5,
    'shoulder_drop': 19,
    'shoulder_front': 4,
    'shoulder_opening': 18,
    'sleeve': 16,
    'standard_collar': 13,
    'standard_hand': 14,
    'tall_back': 2,
    'tall_front': 1,
    'teek': 20,
    'waist': 9,
    'unit': 'cm',
}


def seed_measurements_template():
    template, _ = MeasurementTemplate.objects.get_or_create(
        name='measurements_template',
        defaults={
            'display_name': 'Measurements',
            'display_name_ar': 'Measurements',
            'default_unit': 'cm',
            'display_order': 0,
            'is_active': True,
        },
    )
    for name, (row, col, display_order) in DEFAULT_APP_PDF_GRID.items():
        label = name.replace('_', ' ').title()
        MeasurementField.objects.update_or_create(
            template=template,
            name=name,
            defaults={
                'display_name': label,
                'display_name_ar': label,
                'display_name_ur': label,
                'field_type': 'decimal',
                'is_required': True,
                'display_order': display_order,
                'pdf_grid_row': row,
                'pdf_grid_col': col,
                'is_active': True,
            },
        )
    return template


class SimpleMeasurementPdfTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed_measurements_template()

    def test_pdf_template_prefers_measurements_template(self):
        template = get_pdf_measurement_template()
        self.assertIsNotNone(template)
        self.assertEqual(template.name, 'measurements_template')

    def test_legacy_order_fills_all_twenty_grid_cells(self):
        field_map = build_pdf_field_map()
        cells = build_measurement_grid_cells(
            LEGACY_ORDER,
            field_map,
            'en',
            5,
            4,
            show_all_slots=True,
        )
        self.assertEqual(len(cells), 20)
        self.assertEqual(sum(1 for cell in cells if cell.get('has_value')), 20)

    def test_arabic_pdf_uses_rtl_grid_columns(self):
        from apps.documents.tests import OrderDocumentEngineTest

        case = OrderDocumentEngineTest()
        case.setUp()
        item = case.order.order_items.first()
        item.measurements = dict(LEGACY_ORDER)
        item.save(update_fields=['measurements'])
        seed_measurements_template()

        html, context, _layout = generate_order_html(case.order, lang='ar')
        self.assertTrue(context['is_rtl'])
        self.assertNotIn('meas-grid meas-grid-fixed-cols', html)
        self.assertIn('meas-grid-table', html)

    def test_english_pdf_keeps_ltr_grid_columns(self):
        from apps.documents.tests import OrderDocumentEngineTest

        case = OrderDocumentEngineTest()
        case.setUp()
        item = case.order.order_items.first()
        item.measurements = dict(LEGACY_ORDER)
        item.save(update_fields=['measurements'])
        seed_measurements_template()

        html, context, _layout = generate_order_html(case.order, lang='en')
        self.assertFalse(context['is_rtl'])
        self.assertIn('meas-grid-table', html)
        self.assertIn('dir="ltr"', html)
