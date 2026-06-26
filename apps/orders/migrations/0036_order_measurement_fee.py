from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0035_remaining_payment_session'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='measurement_fee',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0.00'),
                help_text='One-time measurement rider fee snapshot for this order',
                max_digits=10,
            ),
        ),
    ]
