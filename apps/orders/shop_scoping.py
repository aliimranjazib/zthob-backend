"""Order scoping helpers for multi-shop tailor sessions."""

from __future__ import annotations

from django.db.models import Q


def shop_id_from_request(request):
    from apps.tailors.shop_access import get_token_shop_id
    return get_token_shop_id(request)


def resolve_shop_for_tailor_user(tailor_user, shop_id=None):
    """Resolve the TailorProfile shop row for an order owner user."""
    if not tailor_user:
        return None

    from apps.tailors.models import TailorProfile

    if shop_id is not None:
        try:
            shop = TailorProfile.objects.get(id=shop_id)
        except TailorProfile.DoesNotExist:
            return None
        if shop.shop_owner_user_id == tailor_user.id:
            return shop
        return None

    profile = getattr(tailor_user, 'tailor_profile', None)
    if profile:
        return profile

    return TailorProfile.objects.filter(owner=tailor_user).order_by('created_at').first()


def owned_shop_ids_for_user(owner_user):
    from apps.tailors.models import TailorProfile
    return list(
        TailorProfile.objects.filter(owner=owner_user).values_list('id', flat=True)
    )


def user_owns_shop_id(owner_user, shop_id):
    from apps.tailors.models import TailorProfile
    return TailorProfile.objects.filter(id=shop_id, owner=owner_user).exists()


def get_owner_orders_queryset(owner_user, shop_id=None):
    """Cross-shop orders for an owner, optionally filtered to one shop."""
    from apps.orders.models import Order

    owned_ids = owned_shop_ids_for_user(owner_user)
    if not owned_ids:
        return Order.objects.none()

    if shop_id is not None:
        if shop_id not in owned_ids:
            return Order.objects.none()
        owned_ids = [shop_id]

    return Order.objects.filter(
        Q(shop_id__in=owned_ids)
        | Q(shop__isnull=True, tailor=owner_user)
    )


def apply_shop_session_filter(queryset, request):
    """
    Narrow tailor order lists to the JWT active shop when present.

    Legacy tokens without ``shop_id`` keep owner-wide results.
    """
    shop_id = shop_id_from_request(request)
    if shop_id is None:
        return queryset
    return queryset.filter(
        Q(shop_id=shop_id)
        | Q(shop__isnull=True, tailor=_tailor_user_from_queryset(queryset, request))
    )


def _tailor_user_from_queryset(queryset, request):
    from apps.tailors.shop_access import get_shop_owner_user
    return get_shop_owner_user(request.user, shop_id=shop_id_from_request(request))


def attach_shop_to_order_data(validated_data, *, tailor_user, shop_id=None):
    """Set ``shop`` on validated order data when a tailor is assigned."""
    if not tailor_user:
        return validated_data
    shop = resolve_shop_for_tailor_user(tailor_user, shop_id=shop_id)
    if shop:
        validated_data['shop'] = shop
    return validated_data
