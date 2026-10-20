"""Owner plan marketing copy for GET /api/tailors/config/."""

from __future__ import annotations

from apps.tailors.services.plans.constants import (
    FREE_OWNER_MAX_STAFF,
    OWNER_PLUS_MAX_SHOPS,
    OWNER_PLUS_MAX_STAFF,
)
from apps.tailors.services.shop_plans_config import _translate_features

OWNER_PLUS_DISPLAY_MAX_SHOPS = OWNER_PLUS_MAX_SHOPS
OWNER_PLUS_DISPLAY_MAX_STAFF = OWNER_PLUS_MAX_STAFF

FREE_OWNER_PLAN_FEATURES: tuple[tuple[str, str], ...] = (
    (
        'max_shops',
        'One branch',
    ),
    (
        'max_staff',
        'Up to {max_staff} staff',
    ),
    (
        'owner_fabrics',
        'Manage its fabrics, add, update, Assign',
    ),
    (
        'dashboard',
        'Basic Dashboard Order and sales indicators',
    ),
)

PLUS_OWNER_PLAN_FEATURES: tuple[tuple[str, str], ...] = (
    (
        'unlimited_shops',
        'Up to {plus_max_shops} branches',
    ),
    (
        'unlimited_staff',
        'Up to {plus_max_staff} staff',
    ),
    (
        'branch_comparison',
        'Branch performance comparison',
    ),
    (
        'owner_dashboard',
        'Dedicated owner dashboard',
    ),
    (
        'dashboard',
        'Full dashboard',
    ),
    (
        'daily_reports',
        'Daily reports on the dashboard and WhatsApp',
    ),
    (
        'account_statements',
        'Account statements and reports',
    ),
    (
        'smart_analytics',
        'Smart analytics',
    ),
    (
        'onboarding',
        'Onboarding help and data migration',
    ),
    (
        'fabric_inventory',
        'Fabric inventory Management',
    ),
    (
        'app_theme',
        "Custom design for your store's branding and storefront",
    ),
    (
        'tailor_plus_all_branches',
        'All shops enjoy the tailor plus status in owner Plus.',
    ),
)


def build_owner_plans_config(*, language: str, current_tier: str, translate) -> dict:
    if current_tier not in ('free', 'plus'):
        current_tier = 'free'

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
                        'max_staff': FREE_OWNER_MAX_STAFF,
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
                    format_kwargs={
                        'plus_max_shops': OWNER_PLUS_DISPLAY_MAX_SHOPS,
                        'plus_max_staff': OWNER_PLUS_DISPLAY_MAX_STAFF,
                    },
                ),
            },
        ],
    }
