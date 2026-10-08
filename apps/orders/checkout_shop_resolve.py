"""Resolve customer checkout tailor/shop ids (owner user vs shop profile)."""

from __future__ import annotations

from django.contrib.auth import get_user_model

from apps.customers.services.customer_shops import get_customer_visible_shops_queryset
from apps.orders.shop_scoping import resolve_shop_for_tailor_user


def normalize_order_tailor_shop_payload(data: dict) -> tuple[dict, int | None]:
    """
    Return a payload copy where ``tailor`` is the owner user id and ``shop`` is set
    when the client sent a shop profile id (common after multi-shop customer APIs).

    Accepts:
    - ``tailor`` = owner user id (legacy)
    - ``tailor`` = shop profile id (customer app using list ``id``)
    - ``shop`` = shop profile id (preferred alongside ``tailor_user_id``)
    """
    payload = dict(data)
    tailor_raw = payload.get('tailor')
    shop_raw = payload.get('shop')

    if tailor_raw is None and shop_raw is None:
        return payload, None

    User = get_user_model()
    visible = get_customer_visible_shops_queryset()

    shop = None
    if shop_raw is not None:
        try:
            shop = visible.filter(pk=int(shop_raw)).first()
        except (TypeError, ValueError):
            shop = None
        if shop is None:
            payload.pop('shop', None)

    tailor_user = None
    if tailor_raw is not None:
        try:
            tailor_int = int(tailor_raw)
        except (TypeError, ValueError):
            return payload, shop.id if shop else None

        tailor_user = User.objects.filter(pk=tailor_int, role='TAILOR').first()
        if tailor_user is None:
            shop_from_tailor_field = visible.filter(pk=tailor_int).first()
            if shop_from_tailor_field is not None:
                if shop is not None and shop.id != shop_from_tailor_field.id:
                    return payload, shop.id
                shop = shop or shop_from_tailor_field
                tailor_user = shop_from_tailor_field.shop_owner_user

    if tailor_user is not None and shop is None:
        candidate = resolve_shop_for_tailor_user(tailor_user)
        if candidate is not None and visible.filter(pk=candidate.pk).exists():
            shop = candidate

    if tailor_user is not None:
        payload['tailor'] = tailor_user.id
    if shop is not None:
        payload['shop'] = shop.id

    return payload, shop.id if shop else None
