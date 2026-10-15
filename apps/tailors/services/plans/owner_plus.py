"""Owner Plus subscription state and serialization."""

from __future__ import annotations

from django.contrib.auth import get_user_model

from apps.fabrics.models import FabricProduct
from apps.tailors.models import Business, TailorProfile
from apps.tailors.models.subscription import BusinessOwnerPlusSubscription
from apps.tailors.services.plans.constants import (
    FREE_OWNER_CATALOG_PRODUCTS,
    FREE_OWNER_MAX_SHOPS,
    FREE_OWNER_MAX_STAFF,
    FREE_OWNER_REPORT_DAYS,
)
from apps.tailors.services.v2.business import get_business_record

User = get_user_model()


def get_owner_plus_subscription(
    business: Business | int | None,
) -> BusinessOwnerPlusSubscription | None:
    if business is None:
        return None
    business_id = business if isinstance(business, int) else business.id
    try:
        return BusinessOwnerPlusSubscription.objects.select_related('business').get(
            business_id=business_id,
        )
    except BusinessOwnerPlusSubscription.DoesNotExist:
        return None


def is_owner_plus_active(*, business: Business | int | None = None, owner=None) -> bool:
    if business is None and owner is not None:
        business = get_business_record(owner)
    subscription = get_owner_plus_subscription(business)
    if subscription is None:
        return False
    return subscription.is_active_at()


def is_owner_plus_active_for_shop(shop) -> bool:
    if shop is None:
        return False
    if isinstance(shop, int):
        shop = TailorProfile.objects.filter(id=shop).only('owner_id').first()
        if shop is None:
            return False
    owner_id = getattr(shop, 'owner_id', None)
    if owner_id is None:
        return False
    business = Business.objects.filter(owner_id=owner_id, is_active=True).first()
    return is_owner_plus_active(business=business)


def count_owner_catalog_products(business_id: int) -> int:
    return FabricProduct.objects.filter(business_id=business_id).count()


def count_active_shops_for_owner(owner_id: int) -> int:
    return (
        TailorProfile.objects.filter(owner_id=owner_id)
        .exclude(shop_name__isnull=True)
        .exclude(shop_name='')
        .count()
    )


def count_active_staff_for_owner(owner_id: int) -> int:
    from apps.tailors.models import TailorStaffMember

    return TailorStaffMember.objects.filter(owner_id=owner_id, is_active=True).count()


def _owner_usage(*, business: Business | None, owner_id: int | None) -> dict:
    if business is None or owner_id is None:
        return {
            'shops_count': 0,
            'staff_count': 0,
            'owner_catalog_products_count': 0,
        }
    return {
        'shops_count': count_active_shops_for_owner(owner_id),
        'staff_count': count_active_staff_for_owner(owner_id),
        'owner_catalog_products_count': count_owner_catalog_products(business.id),
    }


def serialize_owner_plus(
    business: Business | None,
    *,
    owner_user=None,
    applicable: bool = True,
) -> dict:
    owner_id = owner_user.id if owner_user is not None else None
    subscription = get_owner_plus_subscription(business)
    active = subscription is not None and subscription.is_active_at()

    base_limits = {
        'max_shops': FREE_OWNER_MAX_SHOPS,
        'max_staff': FREE_OWNER_MAX_STAFF,
        'owner_catalog_products': FREE_OWNER_CATALOG_PRODUCTS,
        'report_analytics_days': sorted(FREE_OWNER_REPORT_DAYS),
    }

    if not applicable:
        return {
            'is_active': False,
            'tier': 'free',
            'status': subscription.status if subscription else 'none',
            'current_period_end': (
                subscription.current_period_end.isoformat()
                if subscription and subscription.current_period_end
                else None
            ),
            'limits': base_limits,
            'usage': _owner_usage(business=business, owner_id=owner_id),
            'applicable': False,
        }

    if not active:
        return {
            'is_active': False,
            'tier': 'free',
            'status': subscription.status if subscription else 'none',
            'current_period_end': (
                subscription.current_period_end.isoformat()
                if subscription and subscription.current_period_end
                else None
            ),
            'limits': base_limits,
            'usage': _owner_usage(business=business, owner_id=owner_id),
            'applicable': True,
        }

    return {
        'is_active': True,
        'tier': 'plus',
        'status': subscription.status,
        'current_period_end': (
            subscription.current_period_end.isoformat()
            if subscription.current_period_end
            else None
        ),
        'limits': {
            'max_shops': None,
            'max_staff': None,
            'owner_catalog_products': None,
            'report_analytics_days': None,
        },
        'usage': _owner_usage(business=business, owner_id=owner_id),
        'applicable': True,
    }
