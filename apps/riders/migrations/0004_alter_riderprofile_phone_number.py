# Generated manually to make phone_number nullable

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('riders', '0003_remove_riderprofile_national_id_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='riderprofile',
            name='phone_number',
            field=models.CharField(blank=True, help_text='Primary contact number', max_length=20, null=True),
        ),
    ]

