# Generated manually for adding stitching_price field to Order model

from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0018_alter_order_tailor_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='stitching_price',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0.00'),
                help_text='Total stitching price for order (only for fabric_with_stitching orders)',
                max_digits=10
            ),
        ),
    ]
