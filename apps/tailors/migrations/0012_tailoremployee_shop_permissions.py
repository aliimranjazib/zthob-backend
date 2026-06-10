from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tailors', '0011_fabriccountry_fabric_country_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='tailoremployee',
            name='can_manage_shop_address',
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name='tailoremployee',
            name='can_manage_shop_profile',
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name='tailoremployee',
            name='can_manage_shop_status',
            field=models.BooleanField(db_index=True, default=False),
        ),
    ]
