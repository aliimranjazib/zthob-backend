from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('customization', '0004_alter_customstyle_created_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='measurementtemplate',
            name='display_name_ur',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Urdu display name',
                max_length=100,
            ),
        ),
        migrations.AddField(
            model_name='measurementfield',
            name='display_name_ur',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Urdu label',
                max_length=100,
            ),
        ),
        migrations.AddField(
            model_name='measurementfield',
            name='help_text_ur',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Urdu helper tip for tailor',
                max_length=200,
            ),
        ),
    ]
