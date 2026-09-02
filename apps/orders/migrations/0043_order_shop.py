from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def forwards_backfill_order_shop(apps, schema_editor):
    Order = apps.get_model('orders', 'Order')
    TailorProfile = apps.get_model('tailors', 'TailorProfile')

    for order in Order.objects.filter(tailor_id__isnull=False, shop_id__isnull=True).iterator():
        profile = TailorProfile.objects.filter(user_id=order.tailor_id).first()
        if profile is None:
            profile = (
                TailorProfile.objects.filter(owner_id=order.tailor_id)
                .order_by('created_at')
                .first()
            )
        if profile:
            order.shop_id = profile.id
            order.save(update_fields=['shop_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0042_customer_fabric_images'),
        ('tailors', '0019_tailorstaffmember_shopstaffassignment'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='shop',
            field=models.ForeignKey(
                blank=True,
                help_text='Tailor shop this order belongs to (multi-shop scoping)',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='shop_orders',
                to='tailors.tailorprofile',
            ),
        ),
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['shop', 'status'], name='orders_orde_shop_id_8a1f2b_idx'),
        ),
        migrations.RunPython(forwards_backfill_order_shop, migrations.RunPython.noop),
    ]
