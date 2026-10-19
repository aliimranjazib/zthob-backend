"""Owner plan marketing copy for GET /api/tailors/config/."""

from __future__ import annotations

from apps.tailors.services.plans.constants import (
    FREE_FABRIC_LIMIT_PER_BUCKET,
    FREE_OWNER_MAX_SHOPS,
    FREE_OWNER_MAX_STAFF,
    FREE_OWNER_REPORT_DAYS,
    FREE_OWNER_CATALOG_PRODUCTS,
)
from apps.tailors.services.shop_plans_config import _format_days_list, _translate_features

FREE_OWNER_PLAN_FEATURES: tuple[tuple[str, str], ...] = (
    (
        'max_shops',
        'Up to {max_shops} shop branches',
    ),
    (
        'max_staff',
        'Up to {max_staff} employees',
    ),
    (
        'owner_catalog',
        'Business fabric catalog: up to {catalog_limit} products',
    ),
    (
        'fabric_inventory',
        'Fabric inventory and business-wide stock insights — Owner Plus',
    ),
    (
        'per_shop_fabrics',
        'Each branch: up to {shop_limit} fabrics per shop (see Shop plans)',
    ),
    (
        'owner_reports',
        'Dashboard reports: {days_list}-day views only',
    ),
    (
        'shop_plan_default',
        'Branches use the free shop plan unless you add Tailor Plus per branch',
    ),
    (
        'app_theme',
        'Customize App Theme',
    ),
)

PLUS_OWNER_PLAN_FEATURES: tuple[tuple[str, str], ...] = (
    (
        'unlimited_shops',
        'Unlimited shop branches',
    ),
    (
        'unlimited_staff',
        'Unlimited employees',
    ),
    (
        'unlimited_catalog',
        'Unlimited fabrics in your business catalog',
    ),
    (
        'fabric_inventory',
        'Fabric inventory: stock, movements, and owner-level fabric insights',
    ),
    (
        'tailor_plus_all_branches',
        'Tailor Plus on every branch you own (full shop benefits without separate upgrades)',
    ),
    (
        'owner_reports',
        'Full dashboard reports on all branches',
    ),
    (
        'app_theme',
        'Customize App Theme',
    ),
    (
        'priority_support',
        'Priority support and faster fabric review',
    ),
)


def build_owner_plans_config(*, language: str, current_tier: str, translate) -> dict:
    if current_tier not in ('free', 'plus'):
        current_tier = 'free'

    free_days = _format_days_list(FREE_OWNER_REPORT_DAYS)
    shop_limit = FREE_FABRIC_LIMIT_PER_BUCKET

    return {
        'title': translate('Business plans', language),
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
                'name': translate('Free business plan', language),
                'badge_key': None,
                'features': _translate_features(
                    FREE_OWNER_PLAN_FEATURES,
                    language=language,
                    translate=translate,
                    format_kwargs={
                        'max_shops': FREE_OWNER_MAX_SHOPS,
                        'max_staff': FREE_OWNER_MAX_STAFF,
                        'catalog_limit': FREE_OWNER_CATALOG_PRODUCTS,
                        'days_list': free_days,
                        'shop_limit': shop_limit,
                    },
                ),
            },
            {
                'tier': 'plus',
                'name': translate('Owner Plus', language),
                'badge_key': 'recommended',
                'features': _translate_features(
                    PLUS_OWNER_PLAN_FEATURES,
                    language=language,
                    translate=translate,
                ),
            },
        ],
    }
