# Generated manually for adding read/unread tracking

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='notificationlog',
            name='is_read',
            field=models.BooleanField(default=False, help_text='Whether the user has read this notification'),
        ),
        migrations.AddField(
            model_name='notificationlog',
            name='read_at',
            field=models.DateTimeField(blank=True, help_text='When the notification was read by the user', null=True),
        ),
        migrations.AddIndex(
            model_name='notificationlog',
            index=models.Index(fields=['user', 'is_read'], name='notificatio_user_id_read_idx'),
        ),
    ]


