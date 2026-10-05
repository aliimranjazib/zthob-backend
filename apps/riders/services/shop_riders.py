"""Per-shop rider team helpers."""

from __future__ import annotations

from rest_framework.exceptions import ValidationError

from apps.finance.shop_session import resolve_finance_shop, finance_shop_required_message
from apps.riders.models import TailorRiderAssociation
from apps.tailors.shop_access import get_shop_owner_user


def resolve_rider_session_shop(request):
    """Same shop session as finance (JWT shop_id or single-shop fallback)."""
    return resolve_finance_shop(request)


def require_rider_session_shop(request):
    shop, shop_id = resolve_rider_session_shop(request)
    if not shop or not shop_id:
        raise ValidationError(finance_shop_required_message())
    return shop, shop_id


def get_active_rider_association(*, shop_id, rider_id, tailor_id=None):
    qs = TailorRiderAssociation.objects.filter(
        shop_id=shop_id,
        rider_id=rider_id,
        is_active=True,
    )
    if tailor_id is not None:
        qs = qs.filter(tailor_id=tailor_id)
    return qs.first()


def validate_rider_for_shop(order, rider, assignment_type):
    """
    Ensure rider is on the order shop's team and has the right capability.

    Legacy orders without shop_id keep previous behavior (capability check only when
    an association exists for that shop).
    """
    shop_id = getattr(order, 'shop_id', None)
    if not shop_id:
        association = TailorRiderAssociation.objects.filter(
            tailor_id=order.tailor_id,
            rider=rider,
            is_active=True,
        ).first()
    else:
        association = get_active_rider_association(
            shop_id=shop_id,
            rider_id=rider.id,
            tailor_id=order.tailor_id,
        )

    if not association:
        if shop_id:
            raise ValidationError('This rider is not on your team for this shop.')
        return

    if assignment_type == 'measurement' and not association.can_take_measurements:
        raise ValidationError('This rider is not enabled for measurement assignments.')
    if assignment_type == 'delivery' and not association.can_do_delivery:
        raise ValidationError('This rider is not enabled for delivery assignments.')


def resolve_tailor_user_for_rider_api(request):
    owner = get_shop_owner_user(request.user)
    return owner
