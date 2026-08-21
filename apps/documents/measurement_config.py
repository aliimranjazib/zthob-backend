"""Single source of truth for PDF / studio measurement fields.

The mobile and tailor apps persist measurements using ``measurements_template``
field names (``hem``, ``hips``, ``tall_front``, …). PDF generation and the
layout studio must use that same template — not a parallel thobe template.
"""

from apps.documents.measurement_aliases import LEGACY_TO_CANONICAL

# Prefer the app template; fall back to thobe for dev/test databases.
PDF_MEASUREMENT_TEMPLATE_NAMES = ('measurements_template', 'thobe')

# Default 5×4 grid for legacy app fields (row, col, display_order).
DEFAULT_APP_PDF_GRID = {
    'hem': (1, 1, 1),
    'teek': (1, 2, 4),
    'flipped_collar': (1, 3, 14),
    'chest_upper': (1, 4, 7),
    'cufflink': (1, 5, 12),
    'standard_hand': (2, 1, 15),
    'hips': (2, 2, 5),
    'sleeve': (2, 3, 15),
    'chest_lower': (2, 4, 8),
    'shoulder_front': (2, 5, 13),
    'tall_back': (3, 1, 11),
    'shoulder_back': (3, 2, 17),
    'shoulder_drop': (3, 3, 16),
    'chest_girth': (3, 4, 9),
    'armpit': (3, 5, 19),
    'waist': (4, 1, 3),
    'lower_width': (4, 2, 6),
    'shoulder_opening': (4, 3, 20),
    'tall_front': (4, 4, 10),
    'standard_collar': (4, 5, 20),
}


def get_pdf_measurement_template():
    from apps.customization.models import MeasurementTemplate

    for name in PDF_MEASUREMENT_TEMPLATE_NAMES:
        template = MeasurementTemplate.objects.filter(name=name, is_active=True).first()
        if template is not None:
            return template
    return (
        MeasurementTemplate.objects.filter(is_active=True)
        .order_by('display_order', 'name')
        .first()
    )


def build_pdf_field_map():
    """Field metadata keyed by name for the active PDF measurement template."""
    from apps.customization.models import MeasurementField

    template = get_pdf_measurement_template()
    if template is None:
        return {}

    field_map = {}
    fields = MeasurementField.objects.filter(
        template=template,
        is_active=True,
    ).order_by('display_order', 'name')

    for idx, field in enumerate(fields):
        unit = 'cm'
        if field.template_id and getattr(field.template, 'default_unit', None):
            unit = field.template.default_unit or 'cm'
        field_map[field.name] = {
            'label_en': field.display_name or field.name.replace('_', ' ').title(),
            'label_ar': field.display_name_ar or field.display_name or field.name,
            'label_ur': field.display_name_ur or field.display_name or field.name,
            'order': idx,
            'display_order': field.display_order or (idx + 1),
            'pdf_grid_row': field.pdf_grid_row,
            'pdf_grid_col': field.pdf_grid_col,
            'unit': unit,
            'template': template.name,
        }
    return field_map
