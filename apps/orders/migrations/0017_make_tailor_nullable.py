# Generated manually to make tailor field nullable

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0016_make_fabric_nullable'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='tailor',
            field=models.ForeignKey(
                blank=True,
                help_text='Tailor assigned to this order',
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='tailor_orders',
                to=settings.AUTH_USER_MODEL
            ),
        ),
    ]
