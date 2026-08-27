from decimal import Decimal

from django.db import migrations, models


def enable_existing_measurement_fees(apps, schema_editor):
    TailorProfile = apps.get_model('tailors', 'TailorProfile')
    TailorProfile.objects.filter(measurement_fee__gt=Decimal('0.00')).update(
        is_measurement_fee_enabled=True
    )


def disable_existing_measurement_fees(apps, schema_editor):
    TailorProfile = apps.get_model('tailors', 'TailorProfile')
    TailorProfile.objects.update(is_measurement_fee_enabled=False)


class Migration(migrations.Migration):

    dependencies = [
        ('tailors', '0016_tailorprofile_standard_stitching_days'),
    ]

    operations = [
        migrations.AddField(
            model_name='tailorprofile',
            name='is_measurement_fee_enabled',
            field=models.BooleanField(
                default=False,
                help_text='Whether this tailor charges a measurement fee',
            ),
        ),
        migrations.RunPython(
            enable_existing_measurement_fees,
            disable_existing_measurement_fees,
        ),
    ]
