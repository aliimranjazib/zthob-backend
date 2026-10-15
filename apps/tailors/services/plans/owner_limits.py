"""Owner free-tier limits (shops, staff, catalog, aggregate reports)."""

from __future__ import annotations

from rest_framework.exceptions import ValidationError

from apps.accounts.services.v2_auth import count_active_shops
from apps.fabrics.models import FabricProduct
from apps.tailors.models import Business, TailorStaffMember
from apps.tailors.services.plans.constants import (
    FREE_OWNER_CATALOG_PRODUCTS,
    FREE_OWNER_MAX_SHOPS,
    FREE_OWNER_MAX_STAFF,
    FREE_OWNER_REPORT_DAYS,
)
from apps.tailors.services.plans.owner_plus import is_owner_plus_active
from apps.tailors.services.shop_plus import (
    PLUS_ONLY_REPORT_PERIODS,
    _report_span_days,
)
from apps.orders.history_utils import ALLOWED_PERIODS, resolve_period_bounds


class OwnerPlanLimitError(ValidationError):
    default_code = 'PLAN_LIMIT'

    def __init__(self, detail=None, *, code=None, entitlement=None):
        message = detail if isinstance(detail, str) else 'Owner Plus is required for this action.'
        payload = {'message': message}
        if entitlement:
            payload['entitlement'] = entitlement
        super().__init__(payload, code=code or self.default_code)


def assert_can_create_shop(*, owner, creating_new_named_shop: bool) -> None:
    """Block when free owner would exceed max shops (grandfather existing over limit)."""
    if not creating_new_named_shop:
        return
    if is_owner_plus_active(owner=owner):
        return
    current = count_active_shops(owner.id)
    if current >= FREE_OWNER_MAX_SHOPS:
        raise OwnerPlanLimitError(
            f'Free business accounts can have up to {FREE_OWNER_MAX_SHOPS} shop branches. '
            'Owner Plus unlocks unlimited branches.',
            entitlement='max_shops',
        )


def assert_can_add_staff_member(*, owner, is_new_active_member: bool) -> None:
    if not is_new_active_member:
        return
    if is_owner_plus_active(owner=owner):
        return
    current = TailorStaffMember.objects.filter(owner=owner, is_active=True).count()
    if current >= FREE_OWNER_MAX_STAFF:
        raise OwnerPlanLimitError(
            f'Free business accounts can have up to {FREE_OWNER_MAX_STAFF} employees. '
            'Owner Plus unlocks unlimited staff.',
            entitlement='max_staff',
        )


def assert_can_create_owner_catalog_product(*, business: Business, owner) -> None:
    if is_owner_plus_active(business=business, owner=owner):
        return
    current = FabricProduct.objects.filter(business_id=business.id).count()
    if current >= FREE_OWNER_CATALOG_PRODUCTS:
        raise OwnerPlanLimitError(
            f'Free business accounts can create up to {FREE_OWNER_CATALOG_PRODUCTS} '
            'fabrics in the business catalog. Owner Plus unlocks unlimited fabrics.',
            entitlement='owner_catalog_products',
        )


def validate_report_period_for_owner(
    owner,
    *,
    period: str,
    from_date=None,
    to_date=None,
) -> None:
    """Aggregate owner dashboard reports (no shop_id filter)."""
    if is_owner_plus_active(owner=owner):
        if period not in ALLOWED_PERIODS:
            raise ValueError(f'Invalid period. Must be one of: {", ".join(ALLOWED_PERIODS)}.')
        try:
            resolve_period_bounds(period, from_date=from_date, to_date=to_date)
        except ValidationError as exc:
            raise ValueError(str(exc.detail)) from exc
        return

    if period not in ALLOWED_PERIODS:
        raise ValueError(f'Invalid period. Must be one of: {", ".join(ALLOWED_PERIODS)}.')

    if period in PLUS_ONLY_REPORT_PERIODS:
        raise OwnerPlanLimitError(
            'Owner Plus is required for this report period on the business dashboard.',
            entitlement='owner_reports_period',
        )

    start, end = resolve_period_bounds(period, from_date=from_date, to_date=to_date)
    span = _report_span_days(start, end)
    if span not in FREE_OWNER_REPORT_DAYS:
        raise OwnerPlanLimitError(
            'Free business accounts can view dashboard reports for 1-day or 7-day ranges only. '
            'Owner Plus unlocks all report periods.',
            entitlement='owner_reports_period',
        )
