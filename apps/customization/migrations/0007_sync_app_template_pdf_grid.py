from django.db import migrations

from apps.documents.measurement_config import DEFAULT_APP_PDF_GRID


def sync_app_template_pdf_grid(apps, schema_editor):
    MeasurementTemplate = apps.get_model('customization', 'MeasurementTemplate')
    MeasurementField = apps.get_model('customization', 'MeasurementField')

    app_template = MeasurementTemplate.objects.filter(name='measurements_template').first()
    if app_template is None:
        return

    for legacy_field in MeasurementField.objects.filter(template=app_template, is_active=True):
        grid = DEFAULT_APP_PDF_GRID.get(legacy_field.name)
        if not grid:
            continue
        row, col, display_order = grid
        legacy_field.pdf_grid_row = int(row)
        legacy_field.pdf_grid_col = int(col)
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
