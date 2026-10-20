"""Boolean maps that match shop_plans / owner_plans feature keys."""

from __future__ import annotations

SHOP_FREE_ENTITLEMENTS = (
    'store_setup',
    'add_products',
    'app_orders',
    'app_measurements',
    'choose_driver',
    'weekly_payouts',
    'dashboard_basic',
    'delivery_by_tailor',
)

SHOP_PLUS_ENTITLEMENTS = (
    'walk_in_orders',
    'crm',
    'order_stages',
    'fabric_inventory',
    'shop_only_products',
    'shop_only_measurements',
    'custom_measurement_fields',
    'dashboard_full',
    'customer_reports',
    'whatsapp_messages',
    'app_theme',
    'lower_commission',
    'priority_support',
    'payment_gateway_addon',
    'mgask_delivery_addon',
)

OWNER_FREE_ENTITLEMENTS = (
    'max_shops',
    'max_staff',
    'owner_fabrics',
    'dashboard_basic',
)

OWNER_PLUS_ENTITLEMENTS = (
    'unlimited_shops',
    'unlimited_staff',
    'branch_comparison',
    'owner_dashboard',
    'dashboard_full',
    'daily_reports',
    'account_statements',
    'smart_analytics',
    'onboarding',
    'fabric_inventory',
    'app_theme',
    'tailor_plus_all_branches',
)

SHOP_PLUS_FEATURE_MESSAGES = {
    'walk_in_orders': 'Tailor Plus is required to add in-store orders and walk-in customers.',
    'crm': 'Tailor Plus is required for customer management (CRM).',
    'order_stages': 'Tailor Plus is required for full shop order stages.',
    'fabric_inventory': 'Tailor Plus is required for inventory management.',
    'shop_only_products': 'Tailor Plus is required for shop-only products.',
    'shop_only_measurements': 'Tailor Plus is required for shop-only measurements.',
    'custom_measurement_fields': 'Tailor Plus is required to customize measurement fields for this shop.',
    'dashboard_full': 'Tailor Plus is required for the full shop dashboard.',
    'customer_reports': 'Tailor Plus is required for customer reports.',
    'whatsapp_messages': 'Tailor Plus is required for custom WhatsApp messages.',
    'app_theme': 'Tailor Plus is required to customize store branding.',
    'mgask_delivery_addon': 'Tailor Plus is required for delivery and measurement-taking by Mgask.',
}

OWNER_PLUS_FEATURE_MESSAGES = {
    'unlimited_shops': 'Owner Plus unlocks up to 10 branches.',
    'unlimited_staff': 'Owner Plus unlocks up to 40 staff.',
    'branch_comparison': 'Owner Plus is required for branch performance comparison.',
    'owner_dashboard': 'Owner Plus is required for the dedicated owner dashboard.',
    'dashboard_full': 'Owner Plus is required for the full owner dashboard.',
    'daily_reports': 'Owner Plus is required for daily reports on the dashboard and WhatsApp.',
    'account_statements': 'Owner Plus is required for account statements and reports.',
    'smart_analytics': 'Owner Plus is required for smart analytics.',
    'fabric_inventory': 'Owner Plus is required for fabric inventory management.',
    'app_theme': 'Owner Plus is required to customize store branding.',
}


def build_shop_entitlements(*, is_plus: bool) -> dict[str, bool]:
    allowed = {key: True for key in SHOP_FREE_ENTITLEMENTS}
    allowed.update({key: bool(is_plus) for key in SHOP_PLUS_ENTITLEMENTS})
    return allowed


def build_owner_entitlements(*, is_plus: bool, applicable: bool) -> dict[str, bool]:
    if not applicable:
        allowed = {key: False for key in OWNER_FREE_ENTITLEMENTS}
        allowed.update({key: False for key in OWNER_PLUS_ENTITLEMENTS})
        return allowed
    allowed = {key: True for key in OWNER_FREE_ENTITLEMENTS}
    allowed.update({key: bool(is_plus) for key in OWNER_PLUS_ENTITLEMENTS})
    return allowed
