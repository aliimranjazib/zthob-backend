"""Measurement field metadata shared by PDF output and Layout Studio."""

from apps.documents.measurement_config import build_pdf_field_map, get_pdf_measurement_template


def serialize_measurement_fields_for_studio():
    """Return measurement fields for the PDF/studio template (same keys as the app)."""
    from apps.customization.models import MeasurementField

    template = get_pdf_measurement_template()
    if template is None:
        return []

    field_map = build_pdf_field_map()
    fields = MeasurementField.objects.filter(
        template=template,
        is_active=True,
    ).select_related('template').order_by('display_order', 'name')

    entries = []
    for field in fields:
        meta = field_map.get(field.name, {})
        label_en = meta.get('label_en') or field.display_name or field.name
        entries.append({
            'id': field.id,
            'name': field.name,
            'display_name': field.display_name,
            'display_name_ar': field.display_name_ar,
            'display_name_ur': field.display_name_ur,
            'pdf_label_en': label_en.upper(),
            'display_order': meta.get('display_order', field.display_order),
            'pdf_grid_row': meta.get('pdf_grid_row') or field.pdf_grid_row,
            'pdf_grid_col': meta.get('pdf_grid_col') or field.pdf_grid_col,
            'template': template.name,
        })
    return entries
