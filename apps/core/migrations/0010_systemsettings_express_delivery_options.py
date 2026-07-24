from django.db import migrations, models

from apps.core.express_delivery import default_express_delivery_options


def seed_express_options(apps, schema_editor):
    SystemSettings = apps.get_model('core', 'SystemSettings')
    for settings_obj in SystemSettings.objects.all():
        max_days = settings_obj.express_delivery_max_days or 10
        settings_obj.express_delivery_options = default_express_delivery_options(max_days)
        settings_obj.save(update_fields=['express_delivery_options'])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_simplify_mobileappversionpolicy'),
    ]

    operations = [
        migrations.AddField(
            model_name='systemsettings',
            name='express_delivery_options',
            field=models.JSONField(
                blank=True,
                help_text=(
                    'Admin-managed express duration options shown in tailor config. '
                    'Example: [{"value": 6, "unit": "hours", "label": "6 Hours"}, '
                    '{"value": 1, "unit": "days", "label": "1 Day"}]. '
                    'Leave empty to use defaults (6 Hours + 1..max_days).'
                ),
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name='systemsettings',
            name='express_delivery_max_days',
            field=models.PositiveIntegerField(
                default=10,
                help_text=(
                    'Fallback maximum days used when express_delivery_options is empty '
                    '(default catalog will be 6 Hours + 1..N days).'
                ),
            ),
        ),
        migrations.RunPython(seed_express_options, noop_reverse),
    ]
