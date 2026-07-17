from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


DEFAULT_POLICIES = [
    ('customer', 'ios'),
    ('customer', 'android'),
    ('tailor', 'ios'),
    ('tailor', 'android'),
    ('rider', 'ios'),
    ('rider', 'android'),
]


def seed_mobile_version_policies(apps, schema_editor):
    MobileAppVersionPolicy = apps.get_model('core', 'MobileAppVersionPolicy')
    for app, platform in DEFAULT_POLICIES:
        MobileAppVersionPolicy.objects.get_or_create(
            app=app,
            platform=platform,
            defaults={
                'minimum_version': '1.0.0',
                'latest_version': '1.0.0',
                'force_update_enabled': False,
                'store_url': '',
                'update_title_en': 'Update required',
                'update_title_ar': 'التحديث مطلوب',
                'update_message_en': 'Please update the app to continue.',
                'update_message_ar': 'يرجى تحديث التطبيق للمتابعة.',
                'is_active': True,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_systemsettings_express_delivery_max_days'),
    ]

    operations = [
        migrations.CreateModel(
            name='MobileAppVersionPolicy',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('app', models.CharField(choices=[('customer', 'Customer'), ('tailor', 'Tailor'), ('rider', 'Rider')], max_length=20)),
                ('platform', models.CharField(choices=[('ios', 'iOS'), ('android', 'Android')], max_length=20)),
                ('minimum_version', models.CharField(default='1.0.0', help_text='Minimum allowed app version (semver, e.g. 2.4.0)', max_length=20)),
                ('latest_version', models.CharField(default='1.0.0', help_text='Latest published app version (semver, e.g. 2.5.0)', max_length=20)),
                ('force_update_enabled', models.BooleanField(default=False, help_text='Block app usage when current version is below minimum_version')),
                ('store_url', models.URLField(blank=True, help_text='App Store or Play Store URL for this app/platform')),
                ('update_title_en', models.CharField(default='Update required', help_text='Dialog title shown when an update is available', max_length=120)),
                ('update_title_ar', models.CharField(blank=True, default='التحديث مطلوب', max_length=120)),
                ('update_message_en', models.TextField(default='Please update the app to continue.', help_text='Message shown when an update is available')),
                ('update_message_ar', models.TextField(blank=True, default='يرجى تحديث التطبيق للمتابعة.')),
                ('is_active', models.BooleanField(default=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='updated_mobile_version_policies', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Mobile App Version Policy',
                'verbose_name_plural': 'Mobile App Version Policies',
                'ordering': ['app', 'platform'],
            },
        ),
        migrations.AddIndex(
            model_name='mobileappversionpolicy',
            index=models.Index(fields=['app', 'platform', 'is_active'], name='core_mobile_app_plat_6d0f8d_idx'),
        ),
        migrations.AddConstraint(
            model_name='mobileappversionpolicy',
            constraint=models.UniqueConstraint(fields=('app', 'platform'), name='unique_mobile_version_policy_app_platform'),
        ),
        migrations.RunPython(seed_mobile_version_policies, migrations.RunPython.noop),
    ]
