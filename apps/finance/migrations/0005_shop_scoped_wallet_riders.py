from decimal import Decimal

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


def _recompute_wallet(WalletTransaction, wallet):
    from django.db.models import Sum

    credits = (
        WalletTransaction.objects.filter(wallet=wallet, transaction_type='credit')
        .aggregate(total=Sum('amount'))['total']
        or Decimal('0.00')
    )
    debits = (
        WalletTransaction.objects.filter(wallet=wallet, transaction_type='debit')
        .aggregate(total=Sum('amount'))['total']
        or Decimal('0.00')
    )
    wallet.available_balance = credits - debits
    wallet.total_earned = credits
    wallet.total_withdrawn = debits
    wallet.save(
        update_fields=[
            'available_balance',
            'total_earned',
            'total_withdrawn',
            'updated_at',
        ]
    )


def backfill_tailor_wallets(apps, schema_editor):
    TailorWallet = apps.get_model('finance', 'TailorWallet')
    WalletTransaction = apps.get_model('finance', 'WalletTransaction')
    TailorProfile = apps.get_model('tailors', 'TailorProfile')
    Order = apps.get_model('orders', 'Order')
    PayoutRequest = apps.get_model('finance', 'PayoutRequest')

    for wallet in list(TailorWallet.objects.all()):
        tailor_id = wallet.tailor_id
        shops = _shops_for_tailor(TailorProfile, tailor_id)
        if not shops:
            continue

        if len(shops) == 1:
            wallet.shop_id = shops[0].id
            wallet.save(update_fields=['shop_id', 'updated_at'])
            continue

        shop_wallets = {}
        for shop in shops:
            shop_wallet, _created = TailorWallet.objects.get_or_create(
                tailor_id=tailor_id,
                shop_id=shop.id,
                defaults={
                    'available_balance': Decimal('0.00'),
                    'pending_balance': Decimal('0.00'),
                    'total_earned': Decimal('0.00'),
                    'total_withdrawn': Decimal('0.00'),
                },
            )
            shop_wallets[shop.id] = shop_wallet

        default_shop_id = shops[0].id
        for tx in WalletTransaction.objects.filter(wallet=wallet):
            target_shop_id = default_shop_id
            if tx.order_id:
                order = Order.objects.filter(pk=tx.order_id).only('shop_id').first()
                if order and order.shop_id and order.shop_id in shop_wallets:
                    target_shop_id = order.shop_id
            tx.wallet_id = shop_wallets[target_shop_id].id
            tx.save(update_fields=['wallet_id', 'updated_at'])

        for shop_wallet in shop_wallets.values():
            _recompute_wallet(WalletTransaction, shop_wallet)

        wallet.delete()

    for payout in PayoutRequest.objects.filter(shop__isnull=True):
        debit = (
            WalletTransaction.objects.filter(
                payout_request_id=payout.id,
                transaction_type='debit',
            )
            .select_related('wallet')
            .first()
        )
        if debit and debit.wallet_id:
            wallet = TailorWallet.objects.filter(pk=debit.wallet_id).first()
            if wallet and wallet.shop_id:
                payout.shop_id = wallet.shop_id
                payout.save(update_fields=['shop_id', 'updated_at'])


class Migration(migrations.Migration):

    dependencies = [
        ('tailors', '0022_move_v2_fabrics_to_fabrics_app'),
        ('orders', '0043_order_shop'),
        ('finance', '0004_riderwallettransaction_earning_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='tailorwallet',
            name='shop',
            field=models.ForeignKey(
                blank=True,
                help_text='Shop this wallet belongs to',
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='wallets',
                to='tailors.tailorprofile',
            ),
        ),
        migrations.AddField(
            model_name='payoutrequest',
            name='shop',
            field=models.ForeignKey(
                blank=True,
                help_text='Shop wallet this payout withdraws from',
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='payout_requests',
                to='tailors.tailorprofile',
            ),
        ),
        migrations.AlterField(
            model_name='tailorwallet',
            name='tailor',
            field=models.ForeignKey(
                help_text='The tailor owner user for this wallet',
                limit_choices_to={'role': 'TAILOR'},
                on_delete=django.db.models.deletion.CASCADE,
                related_name='tailor_wallets',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(backfill_tailor_wallets, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='tailorwallet',
            constraint=models.UniqueConstraint(
                fields=('tailor', 'shop'),
                name='uniq_tailor_shop_wallet',
            ),
        ),
    ]
