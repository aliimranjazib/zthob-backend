from django.db import migrations, models
import django.db.models.deletion


def backfill_businesses(apps, schema_editor):
    Business = apps.get_model('tailors', 'Business')
    TailorProfile = apps.get_model('tailors', 'TailorProfile')
    User = apps.get_model('accounts', 'CustomUser')

    owner_ids = (
        TailorProfile.objects.exclude(shop_name__isnull=True)
        .exclude(shop_name='')
        .values_list('owner_id', flat=True)
        .distinct()
    )
    for owner_id in owner_ids:
        if not owner_id or Business.objects.filter(owner_id=owner_id).exists():
            continue
        owner = User.objects.filter(id=owner_id).first()
        if owner is None:
            continue
        first_shop = (
            TailorProfile.objects.filter(owner_id=owner_id)
            .exclude(shop_name__isnull=True)
            .exclude(shop_name='')
            .order_by('id')
            .first()
        )
        shop_count = (
            TailorProfile.objects.filter(owner_id=owner_id)
            .exclude(shop_name__isnull=True)
            .exclude(shop_name='')
            .count()
        )
        setup_step = 'completed' if shop_count else 'business_created'
        if shop_count == 1:
            setup_step = 'first_shop_created'
        elif shop_count > 1:
            setup_step = 'completed'

        business = Business.objects.create(
            owner_id=owner_id,
            name=(first_shop.shop_name if first_shop else '') or owner.get_full_name() or '',
            contact_phone=owner.phone or '',
            status='active' if shop_count else 'draft',
            setup_step=setup_step,
        )
        TailorProfile.objects.filter(owner_id=owner_id).update(business_id=business.id)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_alter_customuser_language'),
        ('tailors', '0019_tailorstaffmember_shopstaffassignment'),
    ]

    operations = [
        migrations.CreateModel(
            name='Business',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, default='', max_length=150)),
                ('contact_phone', models.CharField(blank=True, default='', max_length=20)),
                ('contact_email', models.EmailField(blank=True, null=True)),
                ('city', models.CharField(blank=True, default='', max_length=100)),
                ('logo', models.ImageField(blank=True, null=True, upload_to='business/logos/')),
                ('default_language', models.CharField(default='ar', max_length=10)),
                ('timezone', models.CharField(default='Asia/Riyadh', max_length=64)),
                ('currency', models.CharField(default='SAR', max_length=3)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('active', 'Active'), ('suspended', 'Suspended')], db_index=True, default='draft', max_length=20)),
                ('setup_step', models.CharField(choices=[('business_created', 'Business created'), ('first_shop_created', 'First shop created'), ('completed', 'Completed')], db_index=True, default='business_created', max_length=32)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('owner', models.OneToOneField(help_text='Owner account that owns this business', on_delete=django.db.models.deletion.CASCADE, related_name='business', to='accounts.customuser')),
            ],
            options={
                'verbose_name': 'Business',
                'verbose_name_plural': 'Businesses',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddField(
            model_name='tailorprofile',
            name='business',
            field=models.ForeignKey(blank=True, help_text='Business this shop belongs to', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='shops', to='tailors.business'),
        ),
        migrations.RunPython(backfill_businesses, migrations.RunPython.noop),
    ]
