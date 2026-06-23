from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('riders', '0006_alter_riderorderassignment_created_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='tailorriderassociation',
            name='can_do_delivery',
            field=models.BooleanField(default=True, help_text='Whether this rider can be assigned delivery work for this tailor'),
        ),
        migrations.AddField(
            model_name='tailorriderassociation',
            name='can_take_measurements',
            field=models.BooleanField(default=True, help_text='Whether this rider can be assigned measurement work for this tailor'),
        ),
    ]
