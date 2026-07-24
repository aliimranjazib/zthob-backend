from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tailors', '0014_tailoremployee_can_stitch_orders'),
    ]

    operations = [
        migrations.AddField(
            model_name='tailorprofile',
            name='express_delivery_unit',
            field=models.CharField(
                choices=[('hours', 'Hours'), ('days', 'Days')],
                default='days',
                help_text='Unit for express_delivery_days value (hours or days)',
                max_length=10,
            ),
        ),
        migrations.AlterField(
            model_name='tailorprofile',
            name='express_delivery_days',
            field=models.PositiveIntegerField(
                blank=True,
                help_text=(
                    'Express duration amount. Interpreted with express_delivery_unit '
                    '(e.g. unit=hours and days=6 means 6 hours).'
                ),
                null=True,
            ),
        ),
    ]
