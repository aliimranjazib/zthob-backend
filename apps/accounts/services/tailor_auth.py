"""
Tailor/owner authentication helpers.

Owner-side session fields are additive. Legacy clients that do not use
``app_entry=owner`` keep the original tailor_context shape and JWT claims.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.core.exceptions import PermissionDenied


APP_ENTRY_OWNER = 'owner'
APP_ENTRY_STAFF = 'staff'
ACCESS_MODE_OWNER = 'owner'
ACCESS_MODE_EMPLOYEE = 'employee'
ACCESS_MODE_NONE = 'none'


@dataclass(frozen=True)
class TailorSession:
    shop_id: int | None
    access_mode: str
    app_entry: str | None = None


def build_legacy_tailor_context(user) -> dict[str, Any]:
    """
    Original tailor_context used by the tailor app before owner multi-shop work.

    Employee context still takes priority over owner context.
    """
    context = {
        'is_owner': False,
        'is_employee': False,
        'shop_id': None,
        'roles': [],
        'permissions': {},
    }

    employee = getattr(user, 'tailor_employee', None)
    if employee and employee.is_active:
        context['is_employee'] = True
        context['shop_id'] = employee.tailor_id
        context['roles'] = employee.roles or []
        context['permissions'] = employee.permissions_dict
        return context

    profile = getattr(user, 'tailor_profile', None)
    if profile and profile.shop_name:
        context['is_owner'] = True
        context['shop_id'] = profile.id
    elif not context['is_employee']:
        owned = _owned_shop_queryset(user).exclude(shop_name__isnull=True).exclude(shop_name='').first()
        if owned:
            context['is_owner'] = True
            context['shop_id'] = owned.id

    return context


def _serialize_owned_shop(profile, *, service_area_by_id=None) -> dict[str, Any]:
    service_area = None
    review = getattr(profile, 'review', None)
    if review and review.service_areas:
        area_id = review.service_areas[0]
        area = (service_area_by_id or {}).get(area_id)
        if area is None:
            service_area = {'id': area_id, 'name': None, 'city': None}
        else:
            service_area = {
                'id': area.id,
                'name': area.name,
                'city': area.city,
            }

    return {
        'id': profile.id,
        'shop_name': profile.shop_name or '',
        'contact_number': profile.contact_number,
        'address': profile.address,
        'working_hours': profile.working_hours or {},
        'shop_status': bool(profile.shop_status),
        'is_verified': bool(getattr(profile, 'is_verified', False)),
        'is_pinned': bool(getattr(profile, 'is_pinned', True)),
        'service_area': service_area,
    }


def _owned_shop_queryset(user):
    from apps.tailors.models import TailorProfile

    return (
        TailorProfile.objects.filter(owner=user)
        .select_related('review')
        .exclude(shop_name__isnull=True)
        .exclude(shop_name='')
        .order_by('-is_pinned', '-created_at')
    )


def _service_area_lookup(profiles):
    from apps.tailors.models import ServiceArea

    area_ids = set()
    for profile in profiles:
        review = getattr(profile, 'review', None)
        if review and review.service_areas:
            area_ids.add(review.service_areas[0])
    if not area_ids:
        return {}
    return {
        area.id: area
        for area in ServiceArea.objects.filter(id__in=area_ids)
    }


def _assigned_shop_entries(user) -> list[dict[str, Any]]:
    from apps.tailors.shop_access import get_user_shop_assignments

    entries = []
    for assignment in get_user_shop_assignments(user):
        shop = assignment.shop
        entries.append({
            'id': shop.id,
            'shop_name': shop.shop_name or '',
            'shop_status': bool(shop.shop_status),
            'permissions': assignment.permissions_dict,
            'roles': assignment.roles or [],
        })
    if entries:
        return entries

    employee = getattr(user, 'tailor_employee', None)
    if not employee or not employee.is_active:
        return []

    shop = employee.tailor
    return [{
        'id': shop.id,
        'shop_name': shop.shop_name or '',
        'shop_status': bool(shop.shop_status),
        'permissions': employee.permissions_dict,
        'roles': employee.roles or [],
    }]


def build_owner_auth_context(user, *, app_entry: str = APP_ENTRY_OWNER) -> dict[str, Any]:
    """
    Extended owner/staff auth payload for the owner Flutter shell.

    Always includes legacy keys so older parsers continue to work.
    """
    legacy = build_legacy_tailor_context(user)
    owned_profiles = list(_owned_shop_queryset(user))
    service_area_by_id = _service_area_lookup(owned_profiles)
    owned_shops = [
        _serialize_owned_shop(profile, service_area_by_id=service_area_by_id)
        for profile in owned_profiles
    ]
    assigned_shops = _assigned_shop_entries(user)

    if app_entry == APP_ENTRY_OWNER:
        access_mode = ACCESS_MODE_OWNER
        if owned_shops and not legacy['is_owner']:
            legacy = {
                **legacy,
                'is_owner': True,
                'shop_id': owned_shops[0]['id'],
            }
        active_shop_id = legacy.get('shop_id')
        can_enter_shop_work = bool(owned_shops)
        initial_screen = 'owner_dashboard'
    elif app_entry == APP_ENTRY_STAFF:
        access_mode = ACCESS_MODE_EMPLOYEE if assigned_shops else ACCESS_MODE_NONE
        active_shop_id = assigned_shops[0]['id'] if len(assigned_shops) == 1 else None
        can_enter_shop_work = bool(assigned_shops)
        initial_screen = 'shop_work' if assigned_shops else 'staff_not_assigned'
    else:
        access_mode = ACCESS_MODE_NONE
        active_shop_id = legacy.get('shop_id')
        can_enter_shop_work = bool(legacy.get('shop_id'))
        initial_screen = 'owner_dashboard'

    return {
        **legacy,
        'app_entry': app_entry,
        'mode': app_entry,
        'access_mode': access_mode,
        'active_shop_id': active_shop_id,
        'owned_shops': owned_shops,
        'assigned_shops': assigned_shops,
        'can_enter_shop_work': can_enter_shop_work,
        'routing': {
            'initial_screen': initial_screen,
        },
    }


def build_tailor_auth_context(user, *, app_entry: str | None = None) -> dict[str, Any]:
    if app_entry in (APP_ENTRY_OWNER, APP_ENTRY_STAFF):
        return build_owner_auth_context(user, app_entry=app_entry)
    return build_legacy_tailor_context(user)


def resolve_shop_session(user, shop_id: int) -> TailorSession:
    """
    Validate that the user may act in the given shop and return session metadata.
    """
    from apps.tailors.models import TailorProfile

    try:
        shop = TailorProfile.objects.get(id=shop_id)
    except TailorProfile.DoesNotExist as exc:
        raise PermissionDenied('Shop not found.') from exc

    if shop.owner_id == user.id:
        return TailorSession(shop_id=shop.id, access_mode=ACCESS_MODE_OWNER)

    if shop.user_id == user.id:
        return TailorSession(shop_id=shop.id, access_mode=ACCESS_MODE_OWNER)

    from apps.tailors.shop_access import get_shop_staff_context
    if get_shop_staff_context(user, shop_id=shop.id):
        return TailorSession(shop_id=shop.id, access_mode=ACCESS_MODE_EMPLOYEE)

    raise PermissionDenied('You do not have access to this shop.')


def issue_tailor_tokens(user, *, session: TailorSession | None = None):
    from apps.accounts.serializers import UnifiedRefreshToken

    if session is None:
        return UnifiedRefreshToken.for_user(user)

    kwargs = {
        'shop_id': session.shop_id,
        'access_mode': session.access_mode,
    }
    if session.app_entry is not None:
        kwargs['app_entry'] = session.app_entry
    return UnifiedRefreshToken.for_user(user, **kwargs)


def tokens_payload(refresh) -> dict[str, str]:
    return {
        'access_token': str(refresh.access_token),
        'refresh_token': str(refresh),
    }
