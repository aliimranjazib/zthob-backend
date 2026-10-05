from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def _shops_for_tailor(TailorProfile, tailor_id):
    shops = list(
        TailorProfile.objects.filter(owner_id=tailor_id).order_by('created_at')
    )
    if shops:
        return shops
    return list(TailorProfile.objects.filter(user_id=tailor_id).order_by('created_at'))


def backfill_rider_shop_links(apps, schema_editor):
    from django.db.models import Q

    Association = apps.get_model('riders', 'TailorRiderAssociation')
    InvitationCode = apps.get_model('riders', 'TailorInvitationCode')
    TailorProfile = apps.get_model('tailors', 'TailorProfile')
    Order = apps.get_model('orders', 'Order')

    for assoc in Association.objects.filter(shop__isnull=True):
        tailor_id = assoc.tailor_id
        shop_id = None
        order = (
            Order.objects.filter(tailor_id=tailor_id, shop_id__isnull=False)
            .filter(
                Q(measurement_rider_id=assoc.rider_id)
                | Q(delivery_rider_id=assoc.rider_id)
                | Q(rider_id=assoc.rider_id)
                | Q(assigned_rider_id=assoc.rider_id)
            )
            .order_by('created_at')
            .first()
        )
        if order:
            shop_id = order.shop_id
        if not shop_id:
            shops = _shops_for_tailor(TailorProfile, tailor_id)
            if len(shops) == 1:
                shop_id = shops[0].id
        if shop_id:
            assoc.shop_id = shop_id
            assoc.save(update_fields=['shop_id', 'updated_at'])

    for code in InvitationCode.objects.filter(shop__isnull=True):
        shops = _shops_for_tailor(TailorProfile, code.tailor_id)
        if len(shops) == 1:
            code.shop_id = shops[0].id
            code.save(update_fields=['shop_id', 'updated_at'])


class Migration(migrations.Migration):

    dependencies = [
        ('tailors', '0022_move_v2_fabrics_to_fabrics_app'),
        ('riders', '0007_tailorriderassociation_capabilities'),
    ]

    operations = [
        migrations.AddField(
            model_name='tailorinvitationcode',
            name='shop',
            field=models.ForeignKey(
                blank=True,
                help_text='Shop this invitation code belongs to',
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='rider_invitation_codes',
                to='tailors.tailorprofile',
            ),
        ),
        migrations.AddField(
            model_name='tailorriderassociation',
            name='shop',
            field=models.ForeignKey(
                blank=True,
                help_text='Shop this rider is associated with',
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='rider_associations',
                to='tailors.tailorprofile',
            ),
        ),
        migrations.RunPython(backfill_rider_shop_links, migrations.RunPython.noop),
        migrations.AlterUniqueTogether(
            name='tailorriderassociation',
            unique_together={('shop', 'rider')},
        ),
        migrations.AddIndex(
            model_name='tailorriderassociation',
            index=models.Index(fields=['shop', 'is_active'], name='riders_tail_shop_id_8b2c1a_idx'),
        ),
    ]
