import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0038_stylereferenceimage'),
        ('tailors', '0014_tailoremployee_can_stitch_orders'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='assigned_employee',
            field=models.ForeignKey(
                blank=True,
                help_text=(
                    'Shop employee assigned to stitch this order. '
                    'Null means open to all employees with can_stitch_orders '
                    '(home delivery and walk-in).'
                ),
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='assigned_orders',
                to='tailors.tailoremployee',
            ),
        ),
    ]
