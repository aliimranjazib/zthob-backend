# Generated manually for role-specific rider assignments

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0033_merge_20260611_1023'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='measurement_rider',
            field=models.ForeignKey(
                blank=True,
                help_text='Rider assigned to take customer measurements',
                limit_choices_to={'role': 'RIDER'},
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='measurement_orders',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='order',
            name='delivery_rider',
            field=models.ForeignKey(
                blank=True,
                help_text='Rider assigned to deliver the finished order',
                limit_choices_to={'role': 'RIDER'},
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='delivery_orders',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
