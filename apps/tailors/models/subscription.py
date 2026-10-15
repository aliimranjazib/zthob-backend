"""Shop Tailor Plus and business Owner Plus subscriptions."""

from django.conf import settings
from django.db import models
from django.utils import timezone


class _SubscriptionActiveMixin:
    STATUS_TRIAL = 'trial'
    STATUS_ACTIVE = 'active'
    STATUS_CANCELLED = 'cancelled'
    STATUS_EXPIRED = 'expired'

    def is_active_at(self, moment=None) -> bool:
        moment = moment or timezone.now()
        if self.status not in (self.STATUS_TRIAL, self.STATUS_ACTIVE):
            return False
        if self.current_period_end is None:
            return True
        return moment <= self.current_period_end


class ShopTailorPlusSubscription(_SubscriptionActiveMixin, models.Model):
    STATUS_TRIAL = _SubscriptionActiveMixin.STATUS_TRIAL
    STATUS_ACTIVE = _SubscriptionActiveMixin.STATUS_ACTIVE
    STATUS_CANCELLED = _SubscriptionActiveMixin.STATUS_CANCELLED
    STATUS_EXPIRED = _SubscriptionActiveMixin.STATUS_EXPIRED

    STATUS_CHOICES = (
        (_SubscriptionActiveMixin.STATUS_TRIAL, 'Trial'),
        (_SubscriptionActiveMixin.STATUS_ACTIVE, 'Active'),
        (_SubscriptionActiveMixin.STATUS_CANCELLED, 'Cancelled'),
        (_SubscriptionActiveMixin.STATUS_EXPIRED, 'Expired'),
    )

    shop = models.OneToOneField(
        'tailors.TailorProfile',
        on_delete=models.CASCADE,
        related_name='tailor_plus_subscription',
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
        db_index=True,
    )
    current_period_end = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When set, Plus ends at this time. Leave empty for open-ended admin grants.',
    )
    admin_notes = models.TextField(blank=True, default='')
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='granted_tailor_plus_subscriptions',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Shop Tailor Plus'
        verbose_name_plural = 'Shop Tailor Plus subscriptions'

    def __str__(self):
        return f'Tailor Plus shop_id={self.shop_id} ({self.status})'


class BusinessOwnerPlusSubscription(_SubscriptionActiveMixin, models.Model):
    """Owner/business-level Plus; grants effective Tailor Plus on all owned shops."""

    STATUS_TRIAL = _SubscriptionActiveMixin.STATUS_TRIAL
    STATUS_ACTIVE = _SubscriptionActiveMixin.STATUS_ACTIVE
    STATUS_CANCELLED = _SubscriptionActiveMixin.STATUS_CANCELLED
    STATUS_EXPIRED = _SubscriptionActiveMixin.STATUS_EXPIRED

    STATUS_CHOICES = ShopTailorPlusSubscription.STATUS_CHOICES

    business = models.OneToOneField(
        'tailors.Business',
        on_delete=models.CASCADE,
        related_name='owner_plus_subscription',
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=_SubscriptionActiveMixin.STATUS_ACTIVE,
        db_index=True,
    )
    current_period_end = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When set, Owner Plus ends at this time. Leave empty for open-ended admin grants.',
    )
    admin_notes = models.TextField(blank=True, default='')
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='granted_owner_plus_subscriptions',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Owner Plus'
        verbose_name_plural = 'Owner Plus subscriptions'

    def __str__(self):
        return f'Owner Plus business_id={self.business_id} ({self.status})'
