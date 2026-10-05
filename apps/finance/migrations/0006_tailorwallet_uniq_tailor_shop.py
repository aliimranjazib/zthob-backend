from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0005_shop_scoped_wallet_riders'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='tailorwallet',
            constraint=models.UniqueConstraint(
                fields=('tailor', 'shop'),
                name='uniq_tailor_shop_wallet',
            ),
        ),
    ]
