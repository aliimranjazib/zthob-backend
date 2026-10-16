from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_customuser_appearance'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customuser',
            name='appearance',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='Owner app theme (mode, preset, seed color); synced across devices.',
            ),
        ),
        migrations.AlterField(
            model_name='customuser',
            name='appearance_updated_at',
            field=models.DateTimeField(
                blank=True,
                help_text='Last time appearance preferences were saved.',
                null=True,
            ),
        ),
    ]
