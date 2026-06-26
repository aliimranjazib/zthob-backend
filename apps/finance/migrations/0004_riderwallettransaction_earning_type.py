from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0003_riderpayoutrequest_riderwallet_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='riderwallettransaction',
            name='earning_type',
            field=models.CharField(
                blank=True,
                choices=[('delivery', 'Delivery'), ('measurement', 'Measurement')],
                db_index=True,
                help_text='Rider earning category for order credits',
                max_length=20,
                null=True,
            ),
        ),
        migrations.AddConstraint(
            model_name='riderwallettransaction',
            constraint=models.UniqueConstraint(
                condition=models.Q(('earning_type__isnull', False), ('order__isnull', False)),
                fields=('wallet', 'order', 'transaction_type', 'earning_type'),
                name='uniq_rider_wallet_order_earning_type',
            ),
        ),
    ]
