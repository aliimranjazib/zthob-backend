"""Recompute tailor wallet totals from ledger transactions."""

from __future__ import annotations

from decimal import Decimal

from django.db.models import Sum

from apps.finance.models import TailorWallet, WalletTransaction


def recompute_tailor_wallet_balances(wallet: TailorWallet) -> None:
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
