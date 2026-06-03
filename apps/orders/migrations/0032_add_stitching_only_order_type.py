from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0031_merge_20260601_0933'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='order_type',
            field=models.CharField(
                choices=[
                    ('fabric_only', 'Fabric Purchase Only'),
                    ('fabric_with_stitching', 'Fabric + Stitching'),
                    ('stitching_only', 'Stitching Only'),
                    ('measurement_service', 'Measurement Service Only'),
                ],
                default='fabric_with_stitching',
                help_text='Type of order - fabric only, fabric with stitching, stitching only, or measurement service',
                max_length=25,
            ),
        ),
        migrations.AlterField(
            model_name='order',
            name='stitching_price',
            field=models.DecimalField(
                decimal_places=2,
                default=0.0,
                help_text='Total stitching price for order (for fabric_with_stitching and stitching_only orders)',
                max_digits=10,
            ),
        ),
    ]
