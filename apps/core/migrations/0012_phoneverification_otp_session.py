# Generated manually for OTP session hardening

import uuid

from django.db import migrations, models


def assign_session_ids(apps, schema_editor):
    PhoneVerification = apps.get_model('core', 'PhoneVerification')
    for row in PhoneVerification.objects.filter(session_id__isnull=True).iterator():
        PhoneVerification.objects.filter(pk=row.pk).update(session_id=uuid.uuid4())


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_alter_phoneverification_otp_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='phoneverification',
            name='session_id',
            field=models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, null=True),
        ),
        migrations.AddField(
            model_name='phoneverification',
            name='attempt_count',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='phoneverification',
            name='invalidated_at',
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='phoneverification',
            name='resend_available_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='phoneverification',
            name='otp_hash',
            field=models.CharField(blank=True, max_length=128, null=True),
        ),
        migrations.RunPython(assign_session_ids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='phoneverification',
            name='session_id',
            field=models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
