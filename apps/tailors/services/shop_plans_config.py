"""Shop plan copy for GET /api/tailors/config/ (Free vs Tailor Plus)."""

from __future__ import annotations

from apps.tailors.services.shop_plus import (
    FREE_ANALYTICS_DAYS,
    FREE_FABRIC_LIMIT_PER_BUCKET,
    FREE_REPORT_MAX_DAYS,
    PLUS_ANALYTICS_DAYS,
)

FREE_PLAN_FEATURES: tuple[tuple[str, str], ...] = (
    (
        'shop_created_fabrics',
        'Shop fabric catalog: up to {limit} fabrics you add',
    ),
    (
        'owner_catalog_fabrics',
        'Owner-assigned catalog fabrics: up to {limit} per shop',
    ),
    (
        'fabric_inventory',
        'Fabric inventory and stock tracking — Tailor Plus',
    ),
    (
        'analytics_days',
        'Earnings analytics: {days_list} only',
    ),
    (
        'owner_reports',
        'Branch reports: today, yesterday, or up to {max_days} days custom',
    ),
    (
        'walk_in_measurements_history',
        'Walk-in measurements saved in the customer app',
    ),
    (
        'app_theme',
        'Customize App Theme',
    ),
)

PLUS_PLAN_FEATURES: tuple[tuple[str, str], ...] = (
    (
        'fabric_inventory',
        'Fabric inventory: stock, sales, movements, and shop insights',
    ),
    (
        'shop_created_fabrics',
        'Unlimited shop-added fabrics',
    ),
    (
        'owner_catalog_fabrics',
        'Unlimited owner-assigned fabrics per shop',
    ),
    (
        'custom_measurement_fields',
        'Custom measurement fields for your shop',
    ),
    (
        'analytics_days',
        'Full earnings analytics: {days_list}',
    ),
    (
        'owner_reports',
        'All report periods for every branch',
    ),
    (
        'walk_in_measurements_reuse',
        'Customers can reuse walk-in measurements (faster re-orders)',
    ),
    (
        'fast_payout',
        'Fast payout processing for eligible wallet settlements',
    ),
    (
        'app_theme',
        'Customize App Theme',
    ),
    (
        'priority_support',
        'Priority fabric review and support',
    ),
)


def _format_days_list(days: frozenset[int]) -> str:
    return ', '.join(str(day) for day in sorted(days))


def _translate_features(
    feature_defs: tuple[tuple[str, str], ...],
    *,
    language: str,
    translate,
    format_kwargs: dict | None = None,
) -> list[dict]:
    format_kwargs = format_kwargs or {}
    features = []
    for key, template in feature_defs:
        features.append(
            {
                'key': key,
                'text': translate(template, language, **format_kwargs),
            }
        )
    return features


def build_shop_plans_config(*, language: str, current_tier: str, translate) -> dict:
    """
    Marketing copy for the Shop plans UI.

    ``current_tier`` is ``free`` or ``plus`` (from serialize_shop_tailor_plus).
    """
    limit = FREE_FABRIC_LIMIT_PER_BUCKET
    free_days = _format_days_list(FREE_ANALYTICS_DAYS)
    plus_days = _format_days_list(PLUS_ANALYTICS_DAYS)

    if current_tier not in ('free', 'plus'):
        current_tier = 'free'

    return {
        'title': translate('Shop plans', language),
        'subtitle': translate("Compare plans and see what's included", language),
        'whats_included_heading': translate("What's included", language),
        'current_tier': current_tier,
        'badge_labels': {
            'current': translate('Current', language),
            'recommended': translate('Recommended', language),
        },
        'plans': [
            {
                'tier': 'free',
                'name': translate('Free plan', language),
                'badge_key': None,
                'features': _translate_features(
                    FREE_PLAN_FEATURES,
                    language=language,
                    translate=translate,
                    format_kwargs={
                        'limit': limit,
                        'days_list': free_days,
                        'max_days': FREE_REPORT_MAX_DAYS,
                    },
                ),
            },
            {
                'tier': 'plus',
                'name': translate('Tailor Plus', language),
                'badge_key': 'recommended',
                'features': _translate_features(
                    PLUS_PLAN_FEATURES,
                    language=language,
                    translate=translate,
                    format_kwargs={'days_list': plus_days},
                ),
            },
        ],
    }
