from django.test import TestCase

from apps.documents.measurement_grid import build_measurement_grid_cells, index_fields_by_grid


class MeasurementGridTest(TestCase):
    def test_index_fields_by_grid_uses_first_field_at_position(self):
        field_map = {
            'a': {'pdf_grid_row': 1, 'pdf_grid_col': 1, 'label_en': 'A'},
            'b': {'pdf_grid_row': 1, 'pdf_grid_col': 1, 'label_en': 'B'},
        }
        indexed = index_fields_by_grid(field_map)
        self.assertEqual(indexed[(1, 1)][0], 'a')

    def test_show_all_slots_renders_full_grid_with_empty_values(self):
        field_map = {
            'sleeve_width': {
                'label_en': 'Sleeve Width',
                'display_order': 1,
                'pdf_grid_row': 1,
                'pdf_grid_col': 1,
                'unit': 'cm',
            },
            'waist': {
                'label_en': 'Waist',
                'display_order': 3,
                'pdf_grid_row': 4,
                'pdf_grid_col': 1,
                'unit': 'cm',
            },
        }
        cells = build_measurement_grid_cells(
            {'sleeve_width': 16, 'unit': 'cm'},
            field_map,
            'en',
            5,
            4,
            show_all_slots=True,
        )
        self.assertEqual(len(cells), 20)
        by_key = {cell['key']: cell for cell in cells if cell['key']}
        self.assertTrue(by_key['sleeve_width']['has_value'])
        self.assertFalse(by_key['waist']['has_value'])
        self.assertIsNone(by_key['waist']['value'])
        self.assertEqual(by_key['sleeve_width']['sequence'], 1)
        self.assertEqual(by_key['waist']['sequence'], 3)
