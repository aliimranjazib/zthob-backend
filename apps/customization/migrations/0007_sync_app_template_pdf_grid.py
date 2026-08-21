from django.db import migrations

from apps.documents.measurement_aliases import LEGACY_TO_CANONICAL
from apps.documents.measurement_config import DEFAULT_APP_PDF_GRID


def _grid_for_legacy(legacy_name, thobe_by_name):
    canonical = LEGACY_TO_CANONICAL.get(legacy_name, legacy_name)
    thobe_field = thobe_by_name.get(canonical)
    if thobe_field and thobe_field.pdf_grid_row and thobe_field.pdf_grid_col:
        return (
            thobe_field.pdf_grid_row,
            thobe_field.pdf_grid_col,
            thobe_field.display_order or 0,
        )
    default = DEFAULT_APP_PDF_GRID.get(legacy_name)
    if default:
        return default
    return None


def sync_app_template_pdf_grid(apps, schema_editor):
    MeasurementTemplate = apps.get_model('customization', 'MeasurementTemplate')
    MeasurementField = apps.get_model('customization', 'MeasurementField')

    app_template = MeasurementTemplate.objects.filter(name='measurements_template').first()
    if app_template is None:
        return

    thobe = MeasurementTemplate.objects.filter(name='thobe').first()
    thobe_by_name = {}
    if thobe is not None:
        thobe_by_name = {
            field.name: field
            for field in MeasurementField.objects.filter(template=thobe, is_active=True)
        }

    used_positions = set()
    for legacy_field in MeasurementField.objects.filter(template=app_template, is_active=True):
        grid = _grid_for_legacy(legacy_field.name, thobe_by_name)
        if not grid:
            continue
        row, col, display_order = grid
        pos = (int(row), int(col))
        if pos in used_positions:
            default = DEFAULT_APP_PDF_GRID.get(legacy_field.name)
            if default and (default[0], default[1]) not in used_positions:
                row, col, display_order = default[0], default[1], default[2]
                pos = (int(row), int(col))
            else:
                continue
        used_positions.add(pos)
        legacy_field.pdf_grid_row = int(row)
        legacy_field.pdf_grid_col = int(col)
        if display_order:
            legacy_field.display_order = int(display_order)
        legacy_field.save(update_fields=[
            'pdf_grid_row', 'pdf_grid_col', 'display_order', 'updated_at',
        ])


class Migration(migrations.Migration):

    dependencies = [
        ('customization', '0006_measurementfield_pdf_grid'),
    ]

    operations = [
        migrations.RunPython(sync_app_template_pdf_grid, migrations.RunPython.noop),
    ]
