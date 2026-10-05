"""Resolve active tailor shop for finance APIs (wallet, payouts, shop sales)."""

from __future__ import annotations

from apps.orders.shop_scoping import owned_shop_ids_for_user
from apps.tailors.shop_access import (
    get_shop_owner_user,
    get_shop_staff_context,
    get_tailor_profile,
    resolve_active_shop_id,
)


def resolve_finance_shop(request):
    """
    Return (TailorProfile, shop_id) for the current session.

    Uses JWT shop_id first, then a single owned/assigned shop for legacy sessions.
    Returns (None, None) when the caller must switch shop (multi-shop, no session).
    """
    if request is None:
        return None, None

    user = getattr(request, 'user', None)
    if not user or not getattr(user, 'is_authenticated', False):
        return None, None

    owner_user = get_shop_owner_user(user) or user
    shop_id = resolve_active_shop_id(request)
    if shop_id is not None:
        shop = get_tailor_profile(user, shop_id=shop_id)
        if shop:
            return shop, shop_id

    owned_ids = owned_shop_ids_for_user(owner_user)
    if len(owned_ids) == 1:
        shop = get_tailor_profile(user, shop_id=owned_ids[0])
        if shop:
            return shop, owned_ids[0]

    staff = get_shop_staff_context(user, shop_id=shop_id)
    if staff and getattr(staff, 'tailor_id', None):
        shop = staff.tailor if hasattr(staff, 'tailor') else get_tailor_profile(user, shop_id=staff.tailor_id)
        if shop:
            return shop, shop.id

    shop = get_tailor_profile(user, shop_id=None)
    if shop and not owned_ids:
        return shop, shop.id

    if len(owned_ids) > 1:
        return None, None

    return shop, (shop.id if shop else None)


def finance_shop_required_message():
    return 'Select a shop to view wallet and payouts for that shop.'
