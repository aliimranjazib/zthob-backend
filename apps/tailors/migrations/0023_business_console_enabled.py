from django.db import migrations, models


def backfill_console_enabled(apps, schema_editor):
    Business = apps.get_model('tailors', 'Business')
    TailorProfile = apps.get_model('tailors', 'TailorProfile')

    for business in Business.objects.all().iterator():
        shop_count = (
            TailorProfile.objects.filter(owner_id=business.owner_id)
            .exclude(shop_name__isnull=True)
            .exclude(shop_name='')
            .count()
        )
        business.console_enabled = shop_count >= 2
        business.save(update_fields=['console_enabled'])


class Migration(migrations.Migration):

    dependencies = [
        ('tailors', '0022_move_v2_fabrics_to_fabrics_app'),
    ]

    operations = [
        migrations.AddField(
            model_name='business',
            name='console_enabled',
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text='When True, owner may use the multi-shop business console session.',
            ),
        ),
        migrations.RunPython(backfill_console_enabled, migrations.RunPython.noop),
    ]
