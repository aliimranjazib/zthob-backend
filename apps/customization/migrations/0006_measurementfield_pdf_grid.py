from django.db import migrations, models

from apps.customization.thobe_grid import THOBE_FIELDS


def seed_thobe_measurement_grid(apps, schema_editor):
    MeasurementTemplate = apps.get_model('customization', 'MeasurementTemplate')
    MeasurementField = apps.get_model('customization', 'MeasurementField')

    template, _ = MeasurementTemplate.objects.get_or_create(
        name='thobe',
        defaults={
            'display_name': 'Thobe Measurements',
            'display_name_ar': 'مقاسات الثوب',
            'display_name_ur': 'Thobe Measurements',
            'default_unit': 'cm',
            'display_order': 0,
            'is_active': True,
        },
    )

    for name, display_name, display_name_ar, display_order, pdf_grid_row, pdf_grid_col in THOBE_FIELDS:
        MeasurementField.objects.update_or_create(
            template=template,
            name=name,
            defaults={
                'display_name': display_name,
                'display_name_ar': display_name_ar,
                'field_type': 'decimal',
                'is_required': True,
                'display_order': display_order,
                'pdf_grid_row': pdf_grid_row,
                'pdf_grid_col': pdf_grid_col,
                'is_active': True,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ('customization', '0005_measurement_urdu_labels'),
    ]

    operations = [
        migrations.AddField(
            model_name='measurementfield',
            name='pdf_grid_col',
            field=models.PositiveSmallIntegerField(
                blank=True,
                help_text='PDF grid column (1-based). Leave blank to auto-fill.',
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='measurementfield',
            name='pdf_grid_row',
            field=models.PositiveSmallIntegerField(
                blank=True,
                help_text='PDF grid row (1-based). Leave blank to auto-fill.',
                null=True,
            ),
        ),
        migrations.RunPython(seed_thobe_measurement_grid, migrations.RunPython.noop),
    ]
