from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('customers', '0011_fix_audit_log_index_names'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customerdataauditlog',
            name='source',
            field=models.CharField(
                choices=[
                    ('customer_app', 'Customer App'),
                    ('tailor_pos', 'Tailor POS'),
                    ('rider_app', 'Rider App'),
                    ('system', 'System'),
                ],
                default='system',
                max_length=20,
            ),
        ),
    ]
