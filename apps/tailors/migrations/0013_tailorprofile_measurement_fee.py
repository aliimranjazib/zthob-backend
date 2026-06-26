from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tailors', '0012_tailoremployee_shop_permissions'),
    ]

    operations = [
        migrations.AddField(
            model_name='tailorprofile',
            name='measurement_fee',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0.00'),
                help_text='One-time fee charged when this tailor sends a rider for measurements',
                max_digits=10,
            ),
        ),
    ]
