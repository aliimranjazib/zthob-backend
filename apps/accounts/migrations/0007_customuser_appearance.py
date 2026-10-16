# Generated manually for owner app theme sync

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_alter_customuser_language'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='appearance',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='customuser',
            name='appearance_updated_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
