"""Tailor Plus entitlements and limits (per shop)."""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.fabrics.models import ShopFabric
from apps.orders.history_utils import ALLOWED_PERIODS, resolve_period_bounds
from apps.tailors.models import Fabric, TailorProfile
from apps.tailors.models.subscription import ShopTailorPlusSubscription

FREE_FABRIC_LIMIT_PER_BUCKET = 30
FREE_ANALYTICS_DAYS = frozenset({1, 7})
PLUS_ANALYTICS_DAYS = frozenset({1, 7, 15, 30})
PLUS_ONLY_REPORT_PERIODS = frozenset({'this_week', 'this_month', 'past_6_months'})
FREE_REPORT_MAX_DAYS = 7


class TailorPlusLimitError(ValidationError):
    default_code = 'SUBSCRIPTION_REQUIRED'

    def __init__(self, detail=None, *, code=None, entitlement=None):
        message = detail if isinstance(detail, str) else 'Tailor Plus is required for this action.'
        payload = {'message': message}
        if entitlement:
            payload['entitlement'] = entitlement
        super().__init__(payload, code=code or self.default_code)


def get_shop_plus_subscription(shop: TailorProfile | int | None) -> ShopTailorPlusSubscription | None:
    if shop is None:
        return None
    shop_id = shop if isinstance(shop, int) else shop.id
    try:
        return ShopTailorPlusSubscription.objects.select_related('shop').get(shop_id=shop_id)
    except ShopTailorPlusSubscription.DoesNotExist:
        return None


def is_shop_plus_active(shop: TailorProfile | int | None) -> bool:
    subscription = get_shop_plus_subscription(shop)
    if subscription is None:
        return False
    return subscription.is_active_at()


def serialize_shop_tailor_plus(shop: TailorProfile | int | None) -> dict:
    subscription = get_shop_plus_subscription(shop)
    if subscription is None or not subscription.is_active_at():
        return {
            'is_active': False,
            'tier': 'free',
            'status': subscription.status if subscription else 'none',
            'current_period_end': (
                subscription.current_period_end.isoformat()
                if subscription and subscription.current_period_end
                else None
            ),
            'limits': {
                'owner_catalog_fabrics_per_shop': FREE_FABRIC_LIMIT_PER_BUCKET,
                'shop_created_fabrics_per_shop': FREE_FABRIC_LIMIT_PER_BUCKET,
                'report_max_days': FREE_REPORT_MAX_DAYS,
                'analytics_days': sorted(FREE_ANALYTICS_DAYS),
            },
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
            'owner_catalog_fabrics_per_shop': None,
            'shop_created_fabrics_per_shop': None,
            'report_max_days': None,
            'analytics_days': sorted(PLUS_ANALYTICS_DAYS),
        },
    }


def count_owner_catalog_fabrics_on_shop(shop_id: int) -> int:
    return ShopFabric.objects.filter(
        shop_id=shop_id,
        is_active=True,
        product__show_in_owner_catalog=True,
    ).count()


def count_shop_created_fabrics_on_shop(shop_id: int) -> int:
    v2_count = ShopFabric.objects.filter(
        shop_id=shop_id,
        is_active=True,
        product__show_in_owner_catalog=False,
    ).count()
    legacy_count = Fabric.objects.filter(
        tailor_id=shop_id,
        is_active=True,
        v2_shop_fabric__isnull=True,
    ).count()
    return v2_count + legacy_count


def assert_can_add_fabric_to_shop(*, shop: TailorProfile, owner_catalog: bool) -> None:
    if is_shop_plus_active(shop):
        return
    if owner_catalog:
        current = count_owner_catalog_fabrics_on_shop(shop.id)
        entitlement = 'owner_catalog_fabrics'
        message = (
            f'Free shops can list up to {FREE_FABRIC_LIMIT_PER_BUCKET} owner-catalog fabrics. '
            'Tailor Plus unlocks unlimited fabrics for this shop.'
        )
    else:
        current = count_shop_created_fabrics_on_shop(shop.id)
        entitlement = 'shop_created_fabrics'
        message = (
            f'Free shops can add up to {FREE_FABRIC_LIMIT_PER_BUCKET} shop-created fabrics. '
            'Tailor Plus unlocks unlimited fabrics for this shop.'
        )
    if current >= FREE_FABRIC_LIMIT_PER_BUCKET:
        raise TailorPlusLimitError(message, entitlement=entitlement)


def assert_can_assign_owner_product_to_shop(*, shop: TailorProfile, product, is_new_listing: bool) -> None:
    if not is_new_listing:
        return
    owner_catalog = bool(getattr(product, 'show_in_owner_catalog', True))
    assert_can_add_fabric_to_shop(shop=shop, owner_catalog=owner_catalog)


def validate_analytics_days_for_shop(*, shop: TailorProfile | int | None, days: int) -> None:
    if is_shop_plus_active(shop):
        if days not in PLUS_ANALYTICS_DAYS:
            raise ValidationError({'days': 'Days parameter must be one of: 1, 7, 15, 30.'})
        return
    if days not in FREE_ANALYTICS_DAYS:
        raise TailorPlusLimitError(
            'Tailor Plus is required for analytics longer than 7 days.',
            entitlement='analytics_days',
        )


def _report_span_days(start, end) -> int:
    return max(1, (end - start).days)


def validate_report_period_for_shop(
    shop: TailorProfile,
    *,
    period: str,
    from_date=None,
    to_date=None,
) -> None:
    if period not in ALLOWED_PERIODS:
        raise ValueError(f'Invalid period. Must be one of: {", ".join(ALLOWED_PERIODS)}.')
    if is_shop_plus_active(shop):
        try:
            resolve_period_bounds(period, from_date=from_date, to_date=to_date)
        except ValidationError as exc:
            raise ValueError(str(exc.detail)) from exc
        return

    if period in PLUS_ONLY_REPORT_PERIODS:
        raise TailorPlusLimitError(
            'Tailor Plus is required for this report period on this shop.',
            entitlement='owner_reports_period',
        )

    start, end = resolve_period_bounds(period, from_date=from_date, to_date=to_date)
    if _report_span_days(start, end) > FREE_REPORT_MAX_DAYS:
        raise TailorPlusLimitError(
            'Tailor Plus is required for report date ranges longer than 7 days.',
            entitlement='owner_reports_period',
        )


def report_bounds_for_shop(
    shop: TailorProfile,
    *,
    period: str,
    from_date=None,
    to_date=None,
):
    """Return (start, end) for metrics; free shops are clamped to a rolling 7-day window."""
    start, end = resolve_period_bounds(period, from_date=from_date, to_date=to_date)
    if is_shop_plus_active(shop):
        return start, end, False

    now = timezone.now()
    rolling_start = now - timedelta(days=FREE_REPORT_MAX_DAYS)
    if period in PLUS_ONLY_REPORT_PERIODS or _report_span_days(start, end) > FREE_REPORT_MAX_DAYS:
        return rolling_start, now, True
    return start, end, False


def order_shop_for_measurement_rules(order) -> TailorProfile | None:
    shop = getattr(order, 'shop', None)
    if shop is not None:
        return shop
    from apps.orders.shop_scoping import resolve_shop_for_tailor_user

    return resolve_shop_for_tailor_user(getattr(order, 'tailor', None), shop_id=None)


def should_hide_walk_in_order_from_customer_measurements(order) -> bool:
    if getattr(order, 'service_mode', None) != 'walk_in':
        return False
    shop = order_shop_for_measurement_rules(order)
    return is_shop_plus_active(shop)


def active_plus_shop_ids():
    from django.db.models import Q

    now = timezone.now()
    return ShopTailorPlusSubscription.objects.filter(
        status__in=(
            ShopTailorPlusSubscription.STATUS_TRIAL,
            ShopTailorPlusSubscription.STATUS_ACTIVE,
        ),
    ).filter(
        Q(current_period_end__isnull=True) | Q(current_period_end__gte=now),
    ).values_list('shop_id', flat=True)


def customer_measurements_order_queryset_filter(queryset):
    """Exclude Plus-shop walk-in orders from customer measurement library APIs."""
    from django.db.models import Q

    plus_shop_ids = list(active_plus_shop_ids())
    if not plus_shop_ids:
        return queryset
    return queryset.exclude(Q(service_mode='walk_in') & Q(shop_id__in=plus_shop_ids))
