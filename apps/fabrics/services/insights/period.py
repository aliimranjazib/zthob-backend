"""Date windows for fabric insights. Presets match Tailor Plus analytics days."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from django.utils import timezone

from apps.tailors.services.plans.owner_limits import OwnerPlanLimitError
from apps.tailors.services.plans.owner_plus import is_owner_plus_active
from apps.tailors.services.shop_plus import (
    TailorPlusLimitError,
    is_shop_plus_active,
    validate_analytics_days_for_shop,
)

PRESET_DAYS = {
    '1d': 1,
    '7d': 7,
    '15d': 15,
    '30d': 30,
}
ALLOWED_PRESET_DAYS = frozenset(PRESET_DAYS.values())
FREE_MAX_CUSTOM_DAYS = 7
PLUS_MAX_CUSTOM_DAYS = 366


class InsightPeriodError(ValueError):
    """Invalid period input that is not a plan upgrade."""


@dataclass(frozen=True)
class InsightWindow:
    date_from: date
    date_to: date
    days: int | None
    key: str

    def as_dict(self) -> dict:
        return {
            'key': self.key,
            'days': self.days,
            'date_from': self.date_from.isoformat(),
            'date_to': self.date_to.isoformat(),
        }


def resolve_insight_window(
    *,
    days: int | None = None,
    period: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> InsightWindow:
    if date_from is not None or date_to is not None:
        if date_from is None or date_to is None:
            raise InsightPeriodError('date_from and date_to must be provided together.')
        if date_to < date_from:
            raise InsightPeriodError('date_to must be on or after date_from.')
        span = (date_to - date_from).days + 1
        return InsightWindow(
            date_from=date_from,
            date_to=date_to,
            days=span,
            key='custom',
        )

    if period:
        if period not in PRESET_DAYS:
            raise InsightPeriodError('Period must be one of: 1d, 7d, 15d, 30d.')
        days = PRESET_DAYS[period]
        key = period
    else:
        days = 7 if days is None else days
        key = f'{days}d'

    if days not in ALLOWED_PRESET_DAYS:
        raise InsightPeriodError('Days must be one of: 1, 7, 15, 30.')

    date_to = timezone.localdate()
    date_from = date_to - timedelta(days=days)
    return InsightWindow(date_from=date_from, date_to=date_to, days=days, key=key)


def assert_owner_insight_window(window: InsightWindow, *, business, owner) -> None:
    plus = is_owner_plus_active(business=business, owner=owner)
    if window.key == 'custom':
        span = window.days or 0
        if plus and span > PLUS_MAX_CUSTOM_DAYS:
            raise InsightPeriodError('Date range cannot exceed 366 days.')
        if not plus and span > FREE_MAX_CUSTOM_DAYS:
            raise OwnerPlanLimitError(
                'Free business accounts can view fabric insights for up to 7 days. '
                'Owner Plus unlocks longer ranges.',
                entitlement='owner_reports_period',
            )
        return

    if plus:
        return
    if window.days not in (1, 7):
        raise OwnerPlanLimitError(
            'Free business accounts can view fabric insights for 1-day or 7-day ranges only. '
            'Owner Plus unlocks 15-day and 30-day insights.',
            entitlement='owner_reports_period',
        )


def assert_shop_insight_window(window: InsightWindow, *, shop) -> None:
    plus = is_shop_plus_active(shop)
    if window.key == 'custom':
        span = window.days or 0
        if plus and span > PLUS_MAX_CUSTOM_DAYS:
            raise InsightPeriodError('Date range cannot exceed 366 days.')
        if not plus and span > FREE_MAX_CUSTOM_DAYS:
            raise TailorPlusLimitError(
                'Tailor Plus is required for fabric insights longer than 7 days.',
                entitlement='analytics_days',
            )
        return
    validate_analytics_days_for_shop(shop=shop, days=window.days or 7)
