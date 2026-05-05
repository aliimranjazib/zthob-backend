from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
from apps.core.models import BaseModel

class TailorWallet(BaseModel):
    """
    Tracks the financial balance of a tailor.
    Linked to TailorProfile through the tailor user.
    """
    tailor = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wallet',
        limit_choices_to={'role': 'TAILOR'},
        help_text=_("The tailor who owns this wallet")
    )
    available_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_("Funds available for withdrawal")
    )
    pending_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_("Funds from orders in progress (not yet completed)")
    )
    total_earned = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_("Lifetime earnings of the tailor")
    )
    total_withdrawn = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_("Total amount successfully paid out to the tailor")
    )

    class Meta:
        verbose_name = _("Tailor Wallet")
        verbose_name_plural = _("Tailor Wallets")

    def __str__(self):
        return f"Wallet: {self.tailor.username} - Balance: {self.available_balance}"


class WalletTransaction(BaseModel):
    """
    A ledger entry for every movement of money in a tailor's wallet.
    Used to show history and prevent data integrity issues.
    """
    TRANSACTION_TYPE_CHOICES = (
        ('credit', _('Credit (Earning)')),
        ('debit', _('Debit (Withdrawal)')),
        ('refund', _('Refund')),
    )
    
    SOURCE_CHOICES = (
        ('order', _('Order Payment')),
        ('payout', _('Payout/Withdrawal')),
        ('adjustment', _('Admin Adjustment')),
    )

    wallet = models.ForeignKey(
        TailorWallet,
        on_delete=models.CASCADE,
        related_name='transactions',
        help_text=_("The wallet this transaction belongs to")
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPE_CHOICES
    )
    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='wallet_transactions',
        help_text=_("Associated order (if applicable)")
    )
    payout_request = models.ForeignKey(
        'finance.PayoutRequest',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='wallet_transactions',
        help_text=_("Associated payout request (if applicable)")
    )
    description = models.TextField(
        blank=True,
        help_text=_("Detailed description of the transaction")
    )
    running_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        help_text=_("Wallet balance after this transaction (snapshot)")
    )

    class Meta:
        verbose_name = _("Wallet Transaction")
        verbose_name_plural = _("Wallet Transactions")
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.transaction_type.upper()} | {self.amount} | {self.wallet.tailor.username}"


class PayoutRequest(BaseModel):
    """
    Tracks requests made by tailors to withdraw funds to their bank accounts.
    """
    STATUS_CHOICES = (
        ('pending', _('Pending')),
        ('approved', _('Approved')),
        ('rejected', _('Rejected')),
        ('paid', _('Paid/Completed')),
    )

    tailor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payout_requests',
        limit_choices_to={'role': 'TAILOR'}
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    bank_name = models.CharField(max_length=100, blank=True)
    account_number = models.CharField(max_length=50, blank=True)
    iban = models.CharField(max_length=50, blank=True)
    account_holder_name = models.CharField(max_length=100, blank=True)
    
    admin_notes = models.TextField(
        blank=True,
        help_text=_("Notes from admin regarding approval/rejection/payment")
    )
    payment_reference = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("Reference ID from the bank transfer or ClickPay")
    )
    processed_at = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_payouts'
    )

    class Meta:
        verbose_name = _("Payout Request")
        verbose_name_plural = _("Payout Requests")
        ordering = ['-created_at']

    def __str__(self):
        return f"Payout {self.amount} - {self.tailor.username} ({self.status})"
