from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('orders', '0039_order_assigned_employee'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='rejection_reason_code',
            field=models.CharField(
                blank=True,
                help_text='Predefined rejection reason key when tailor rejects a COD order',
                max_length=50,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='order',
            name='rejection_reason',
            field=models.TextField(
                blank=True,
                help_text='Human-readable rejection reason shown to customer/admin',
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='order',
            name='rejected_by',
            field=models.ForeignKey(
                blank=True,
                help_text='User who rejected the order',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='rejected_orders',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
