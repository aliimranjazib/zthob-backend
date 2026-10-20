"""Shop plan copy for GET /api/tailors/config/ (Free vs Tailor Plus)."""

from __future__ import annotations

FREE_PLAN_FEATURES: tuple[tuple[str, str], ...] = (
    (
        'store_setup',
        'Open and set up a store through our sales platform',
    ),
    (
        'add_products',
        'Add products',
    ),
    (
        'app_orders',
        'Receive and manage app orders',
    ),
    (
        'app_measurements',
        'Measurements for app orders',
    ),
    (
        'choose_driver',
        'Choose a driver for orders',
    ),
    (
        'weekly_payouts',
        'Online sales paid out every week',
    ),
    (
        'dashboard',
        'Basic dashboard',
    ),
    (
        'delivery',
        'Delivery and measurements managed by the tailor',
    ),
)

PLUS_PLAN_FEATURES: tuple[tuple[str, str], ...] = (
    (
        'walk_in_orders',
        'Add in-store orders and walk-in customers',
    ),
    (
        'crm',
        'Customer management (CRM)',
    ),
    (
        'order_stages',
        'Order stages: measuring, cutting, sewing, fitting, ready, delivered',
    ),
    (
        'fabric_inventory',
        'Inventory management',
    ),
    (
        'shop_only_products',
        'Shop-only products',
    ),
    (
        'shop_only_measurements',
        'Shop-only measurements',
    ),
    (
        'custom_measurement_fields',
        'Customisable measurement sheet (PDF)',
    ),
    (
        'dashboard',
        'Full dashboard',
    ),
    (
        'customer_reports',
        'Customer reports',
    ),
    (
        'whatsapp_messages',
        'Custom WhatsApp messages to your customers',
    ),
    (
        'app_theme',
        "Custom design for your store's branding and storefront",
    ),
    (
        'lower_commission',
        'Lower commission on platform orders',
    ),
    (
        'priority_support',
        'Advanced technical support with higher priority',
    ),
    (
        'payment_gateway_addon',
        'Dedicated payment gateway (add-on)',
    ),
    (
        'mgask_delivery_addon',
        'Delivery and measurement-taking by Mgask (as agreed)',
    ),
)

OWNER_ONLY_FEATURE_KEYS = frozenset({
    'max_shops',
    'max_staff',
    'unlimited_shops',
    'unlimited_staff',
    'owner_dashboard',
    'branch_comparison',
    'daily_reports',
    'account_statements',
    'smart_analytics',
    'onboarding',
    'owner_fabrics',
    'tailor_plus_all_branches',
})


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
                ),
            },
        ],
    }
