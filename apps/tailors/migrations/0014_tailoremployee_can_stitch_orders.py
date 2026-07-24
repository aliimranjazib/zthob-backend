from django.db import migrations, models


def backfill_stitch_permission(apps, schema_editor):
    TailorEmployee = apps.get_model('tailors', 'TailorEmployee')
    stitch_roles = {'stitcher', 'cutter', 'finisher'}
    for employee in TailorEmployee.objects.all().iterator():
        roles = set(employee.roles or [])
        if roles & stitch_roles or employee.can_manage_orders:
            employee.can_stitch_orders = True
            employee.save(update_fields=['can_stitch_orders'])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('tailors', '0013_tailorprofile_measurement_fee'),
    ]

    operations = [
        migrations.AddField(
            model_name='tailoremployee',
            name='can_stitch_orders',
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text='Can be assigned to stitch orders and see open stitching jobs',
            ),
        ),
        migrations.RunPython(backfill_stitch_permission, noop_reverse),
    ]
