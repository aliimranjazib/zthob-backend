from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0040_order_rejection_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderitem',
            name='recipient_type',
            field=models.CharField(
                choices=[('customer', 'Customer'), ('family_member', 'Family Member')],
                default='customer',
                help_text='Snapshot of who this item is for at order time',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='orderitem',
            name='recipient_display_name',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Immutable display name captured at order creation',
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name='orderitem',
            name='recipient_relationship',
            field=models.CharField(
                blank=True,
                help_text='Immutable relationship snapshot captured at order creation',
                max_length=50,
                null=True,
            ),
        ),
    ]
