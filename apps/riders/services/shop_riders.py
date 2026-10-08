"""Per-shop rider team helpers."""

from __future__ import annotations

from rest_framework.exceptions import ValidationError

from apps.finance.shop_session import resolve_finance_shop, finance_shop_required_message
from apps.core.phone_utils import format_phone_for_display
from apps.riders.models import TailorRiderAssociation
from apps.tailors.shop_access import get_shop_owner_user


def order_shop_profile(order):
    """Shop row for this order (multi-shop), else legacy primary tailor_profile."""
    shop = getattr(order, 'shop', None)
    if shop is not None:
        return shop
    tailor = getattr(order, 'tailor', None)
    if tailor is None:
        return None
    return getattr(tailor, 'tailor_profile', None)


def order_shop_display_name(order):
    profile = order_shop_profile(order)
    if profile and (profile.shop_name or '').strip():
        return profile.shop_name
    tailor = getattr(order, 'tailor', None)
    if tailor:
        return tailor.username
    return 'Unknown'


def rider_order_tailor_address(tailor_user, shop_profile):
    """Structured pickup address for rider order APIs (same shape as before)."""
    address = None
    if tailor_user is not None:
        addresses = tailor_user.addresses.all()
        address = next((addr for addr in addresses if addr.is_default), None)
        if not address:
            address = next(iter(addresses), None)

    if address:
        payload = {
            'id': address.id,
            'latitude': address.latitude,
            'longitude': address.longitude,
            'address': address.address or '',
            'extra_info': address.extra_info or '',
            'is_default': address.is_default,
            'address_tag': address.address_tag,
        }
    elif shop_profile and (shop_profile.address or '').strip():
        payload = {
            'id': None,
            'latitude': None,
            'longitude': None,
            'address': shop_profile.address.strip(),
            'extra_info': '',
            'is_default': False,
            'address_tag': 'shop',
        }
    else:
        return None

    if shop_profile and (shop_profile.address or '').strip():
        payload['address'] = shop_profile.address.strip()

    return payload


def _phone_for_shop(shop, tailor):
    raw_phone = ''
    if shop and shop.contact_number:
        raw_phone = shop.contact_number
    else:
        legacy_profile = getattr(tailor, 'tailor_profile', None)
        if legacy_profile and legacy_profile.contact_number:
            raw_phone = legacy_profile.contact_number
        else:
            raw_phone = getattr(tailor, 'phone', '') or ''
    return format_phone_for_display(raw_phone) if raw_phone else ''


def build_rider_team_shop_payload(association, *, include_roles=False):
    """
    Shop-scoped tailor team row for rider APIs (join + my-tailors).

    Uses association.shop, not tailor.tailor_profile (legacy first shop).
    """
    shop = association.shop
    tailor = association.tailor
    legacy_profile = getattr(tailor, 'tailor_profile', None)

    if shop and (shop.shop_name or '').strip():
        shop_name = shop.shop_name
    elif legacy_profile and (legacy_profile.shop_name or '').strip():
        shop_name = legacy_profile.shop_name
    else:
        shop_name = tailor.username

    payload = {
        'id': tailor.id,
        'tailor_id': tailor.id,
        'shop_id': shop.id if shop else None,
        'shop_name': shop_name,
        'phone': _phone_for_shop(shop, tailor),
    }
    if include_roles:
        payload.update(
            {
                'joined_at': association.created_at,
                'can_take_measurements': association.can_take_measurements,
                'can_do_delivery': association.can_do_delivery,
                'rider_types': [
                    role
                    for role, enabled in (
                        ('measurement', association.can_take_measurements),
                        ('delivery', association.can_do_delivery),
                    )
                    if enabled
                ],
            }
        )
    return payload


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
