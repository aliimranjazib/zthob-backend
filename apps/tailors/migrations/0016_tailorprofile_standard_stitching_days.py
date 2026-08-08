from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tailors', '0015_tailorprofile_express_delivery_unit'),
    ]

    operations = [
        migrations.AddField(
            model_name='tailorprofile',
            name='standard_stitching_days',
            field=models.PositiveIntegerField(
                blank=True,
                help_text='Default standard stitching turnaround in days for this shop',
                null=True,
            ),
        ),
    ]
