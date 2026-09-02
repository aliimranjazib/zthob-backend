from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def forwards_copy_user_to_owner(apps, schema_editor):
    TailorProfile = apps.get_model('tailors', 'TailorProfile')
    for profile in TailorProfile.objects.all().iterator():
        if profile.user_id and profile.owner_id is None:
            profile.owner_id = profile.user_id
            profile.save(update_fields=['owner_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('tailors', '0017_tailorprofile_is_measurement_fee_enabled'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='tailorprofile',
            name='owner',
            field=models.ForeignKey(
                blank=True,
                help_text='Shop owner who manages this tailor shop',
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='owned_shops',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='tailorprofile',
            name='is_pinned',
            field=models.BooleanField(
                default=True,
                help_text='Whether this shop appears in the owner quick-access list',
            ),
        ),
        migrations.RunPython(forwards_copy_user_to_owner, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='tailorprofile',
            name='owner',
            field=models.ForeignKey(
                help_text='Shop owner who manages this tailor shop',
                on_delete=django.db.models.deletion.CASCADE,
                related_name='owned_shops',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name='tailorprofile',
            name='user',
            field=models.OneToOneField(
                blank=True,
                help_text='Legacy primary profile link for backward compatibility',
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='tailor_profile',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
