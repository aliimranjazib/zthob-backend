from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('tailors', '0023_business_console_enabled'),
    ]

    operations = [
        migrations.CreateModel(
            name='ShopTailorPlusSubscription',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(
                    choices=[
                        ('trial', 'Trial'),
                        ('active', 'Active'),
                        ('cancelled', 'Cancelled'),
                        ('expired', 'Expired'),
                    ],
                    db_index=True,
                    default='active',
                    max_length=20,
                )),
                ('current_period_end', models.DateTimeField(
                    blank=True,
                    help_text='When set, Plus ends at this time. Leave empty for open-ended admin grants.',
                    null=True,
                )),
                ('admin_notes', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('granted_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='granted_tailor_plus_subscriptions',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('shop', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='tailor_plus_subscription',
                    to='tailors.tailorprofile',
                )),
            ],
            options={
                'verbose_name': 'Shop Tailor Plus',
                'verbose_name_plural': 'Shop Tailor Plus subscriptions',
            },
        ),
    ]
