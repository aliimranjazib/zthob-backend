from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_rename_core_mobile_app_plat_6d0f8d_idx_core_mobile_app_8f1e46_idx'),
    ]

    operations = [
        migrations.AddField(
            model_name='mobileappversionpolicy',
            name='soft_update_enabled',
            field=models.BooleanField(
                default=False,
                help_text='Show optional update when app version is below latest_version',
            ),
        ),
        migrations.RemoveField(
            model_name='mobileappversionpolicy',
            name='minimum_version',
        ),
        migrations.RemoveField(
            model_name='mobileappversionpolicy',
            name='store_url',
        ),
        migrations.RemoveField(
            model_name='mobileappversionpolicy',
            name='update_message_ar',
        ),
        migrations.RemoveField(
            model_name='mobileappversionpolicy',
            name='update_message_en',
        ),
        migrations.RemoveField(
            model_name='mobileappversionpolicy',
            name='update_title_ar',
        ),
        migrations.RemoveField(
            model_name='mobileappversionpolicy',
            name='update_title_en',
        ),
        migrations.AlterField(
            model_name='mobileappversionpolicy',
            name='force_update_enabled',
            field=models.BooleanField(
                default=False,
                help_text='Block app when version is below latest_version',
            ),
        ),
        migrations.AlterField(
            model_name='mobileappversionpolicy',
            name='latest_version',
            field=models.CharField(
                default='1.0.0',
                help_text='Required app version in the store (semver, e.g. 1.0.27)',
                max_length=20,
            ),
        ),
    ]
