from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0031_merge_20260601_0933'),
    ]

    operations = [
        migrations.AlterField(
            model_name='checkoutsession',
            name='status',
            field=models.CharField(
                choices=[
                    ('active', 'Active'),
                    ('payment_initiated', 'Payment Initiated'),
                    ('order_created', 'Order Created'),
                    ('expired', 'Expired'),
                    ('cancelled', 'Cancelled'),
                    ('payment_failed', 'Payment Failed'),
                ],
                db_index=True,
                default='active',
                max_length=20,
            ),
        ),
    ]
