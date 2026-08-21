"""Measurement field metadata shared by PDF output and Layout Studio."""


def serialize_measurement_fields_for_studio():
    """
    Return measurement fields exactly as the order PDF resolves them.

    Uses the same name de-duplication and label source as ``_measurement_field_map``
    so studio chip labels match downloaded PDF labels (e.g. HEM, TALL BACK).
    """
    from apps.customization.models import MeasurementField
    from apps.tailors.services.order_pdf import _measurement_field_map

    field_map = _measurement_field_map()
    if not field_map:
        return []

    names = list(field_map.keys())
    db_fields = {
        field.name: field
        for field in MeasurementField.objects.filter(
            name__in=names,
            is_active=True,
            template__is_active=True,
        ).select_related('template')
    }

    entries = []
    for name in names:
        field = db_fields.get(name)
        if field is None:
            continue
        meta = field_map[name]
        label_en = meta.get('label_en') or field.display_name or name
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
            'template': field.template.name,
        })

    entries.sort(key=lambda item: (item['display_order'], item['name']))
    return entries
