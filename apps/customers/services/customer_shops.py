"""Customer-facing tailor shop discovery (multi-shop aware)."""

from __future__ import annotations

from django.db.models import Prefetch, Q

from apps.customers.models import Address
from apps.tailors.models import TailorProfile


def get_customer_visible_shops_queryset(*, nearby_owner_or_user_ids=None):
    """
    Approved, open shops shown to customers.

    Uses owner account activity (not legacy profile.user) so extra branches with
    user=null still appear after publish.
    """
    queryset = (
        TailorProfile.objects.filter(
            review__review_status='approved',
            shop_status=True,
            owner__is_active=True,
        )
        .exclude(shop_name__isnull=True)
        .exclude(shop_name='')
        .select_related('owner', 'user', 'review')
        .prefetch_related(
            Prefetch(
                'owner__addresses',
                queryset=Address.objects.filter(is_default=True),
            ),
            Prefetch(
                'user__addresses',
                queryset=Address.objects.filter(is_default=True),
            ),
        )
    )
    if nearby_owner_or_user_ids is not None:
        queryset = queryset.filter(
            Q(owner_id__in=nearby_owner_or_user_ids)
            | Q(user_id__in=nearby_owner_or_user_ids)
        )
    return queryset


def resolve_customer_shop(identifier: int) -> TailorProfile | None:
    """
    Resolve a customer shop by smart id: TailorProfile pk (preferred) or legacy
    tailor user id (primary linked profile only).
    """
    qs = get_customer_visible_shops_queryset()
    shop = qs.filter(pk=identifier).first()
    if shop is not None:
        return shop
    return qs.filter(user_id=identifier).first()


def apply_customer_shop_geo_filter(queryset, nearby_user_ids):
    """Filter shops when any branch owner/user address is within radius."""
    if nearby_user_ids is None:
        return queryset
    return queryset.filter(
        Q(owner_id__in=nearby_user_ids) | Q(user_id__in=nearby_user_ids)
    )
