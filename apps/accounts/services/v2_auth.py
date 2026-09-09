"""V2 authentication and session helpers."""

from __future__ import annotations

from typing import Any

from django.core.exceptions import PermissionDenied

from apps.accounts.services.tailor_auth import (
    APP_ENTRY_OWNER,
    APP_ENTRY_STAFF,
    ACCESS_MODE_EMPLOYEE,
    ACCESS_MODE_OWNER,
    TailorSession,
    issue_tailor_tokens,
    resolve_shop_session,
    tokens_payload,
)
from apps.tailors.models import Business, ShopStaffAssignment, TailorProfile
from apps.tailors.models.staff import STAFF_PERMISSION_KEYS

APP_ENTRY_TAILOR = 'tailor'
V2_APP_ENTRIES = {APP_ENTRY_OWNER, APP_ENTRY_STAFF, APP_ENTRY_TAILOR}

OWNER_PERMISSIONS = {
    'can_manage_business': True,
    'can_manage_shops': True,
    'can_manage_staff': True,
    'can_manage_catalog': True,
    'can_view_reports': True,
    'can_manage_orders': True,
}


def normalize_v2_app_entry(app_entry: str | None) -> str | None:
    if app_entry in (None, ''):
        return None
    value = str(app_entry).strip().lower()
    if value not in V2_APP_ENTRIES:
        raise PermissionDenied(f'Invalid app_entry: {app_entry}')
    return value


def _active_shops_queryset(owner_id: int):
    return (
        TailorProfile.objects.filter(owner_id=owner_id)
        .exclude(shop_name__isnull=True)
        .exclude(shop_name='')
    )


def resolve_membership_type(user) -> str:
    if Business.objects.filter(owner_id=user.id, is_active=True).exists():
        return 'owner'
    if _active_shops_queryset(user.id).exists():
        return 'owner'
    assignment_exists = ShopStaffAssignment.objects.filter(
        staff_member__user_id=user.id,
        staff_member__is_active=True,
        is_active=True,
    ).exists()
    if assignment_exists:
        return 'staff'
    if getattr(user, 'tailor_profile', None) is not None:
        return 'tailor'
    return 'none'


def validate_app_entry_for_user(user, app_entry: str | None) -> str | None:
    app_entry = normalize_v2_app_entry(app_entry)
    if app_entry is None:
        return None

    membership_type = resolve_membership_type(user)
    if app_entry == APP_ENTRY_OWNER:
        if membership_type == 'staff' and not _active_shops_queryset(user.id).exists():
            raise PermissionDenied('This account is staff-only. Use app_entry=staff.')
        return app_entry
    if app_entry == APP_ENTRY_STAFF:
        if membership_type == 'owner':
            return app_entry
        if membership_type != 'staff':
            raise PermissionDenied('This account is not assigned as staff.')
        return app_entry
    if app_entry == APP_ENTRY_TAILOR:
        return app_entry
    return app_entry


def get_business_for_owner(user) -> Business | None:
    return (
        Business.objects.filter(owner_id=user.id, is_active=True)
        .only(
            'id',
            'name',
            'contact_phone',
            'contact_email',
            'city',
            'logo',
            'default_language',
            'timezone',
            'currency',
            'status',
            'setup_step',
            'is_active',
            'created_at',
            'updated_at',
        )
        .first()
    )


def count_active_shops(owner_id: int) -> int:
    return _active_shops_queryset(owner_id).count()


def count_assigned_shops(user_id: int) -> int:
    return (
        ShopStaffAssignment.objects.filter(
            staff_member__user_id=user_id,
            staff_member__is_active=True,
            is_active=True,
        )
        .values('shop_id')
        .distinct()
        .count()
    )


def build_onboarding_flags(user, *, app_entry: str | None) -> dict[str, bool]:
    business = get_business_for_owner(user)
    shops_count = count_active_shops(user.id)
    profile_complete = bool((user.first_name or '').strip() or (user.last_name or '').strip())

    needs_business = app_entry == APP_ENTRY_OWNER and business is None
    needs_shop = shops_count == 0 and app_entry in {APP_ENTRY_OWNER, APP_ENTRY_TAILOR}
    needs_profile_completion = not profile_complete and app_entry in V2_APP_ENTRIES

    return {
        'needs_business': needs_business,
        'needs_shop': needs_shop,
        'needs_profile_completion': needs_profile_completion,
    }


def build_membership_payload(user, *, app_entry: str | None) -> dict[str, Any]:
    membership_type = resolve_membership_type(user)
    if app_entry == APP_ENTRY_STAFF:
        membership_type = 'staff'
    elif app_entry == APP_ENTRY_TAILOR and membership_type == 'none':
        membership_type = 'tailor'
    elif app_entry == APP_ENTRY_OWNER:
        membership_type = 'owner'

    business = get_business_for_owner(user)
    return {
        'type': membership_type,
        'business': serialize_business(business),
    }


def serialize_business(business: Business | None) -> dict[str, Any] | None:
    if business is None:
        return {
            'id': None,
            'name': None,
            'is_setup_complete': False,
        }
    return {
        'id': business.id,
        'name': business.name or None,
        'contact_phone': business.contact_phone or None,
        'contact_email': business.contact_email,
        'city': business.city or None,
        'logo_url': business.logo.url if business.logo else None,
        'default_language': business.default_language,
        'timezone': business.timezone,
        'currency': business.currency,
        'status': business.status,
        'setup_step': business.setup_step,
        'is_setup_complete': business.is_setup_complete,
    }


def build_permissions_payload(user, *, app_entry: str | None) -> dict[str, bool]:
    if app_entry == APP_ENTRY_OWNER or resolve_membership_type(user) == 'owner':
        return dict(OWNER_PERMISSIONS)

    if app_entry == APP_ENTRY_STAFF or resolve_membership_type(user) == 'staff':
        assignment = (
            ShopStaffAssignment.objects.filter(
                staff_member__user_id=user.id,
                staff_member__is_active=True,
                is_active=True,
            )
            .order_by('-updated_at')
            .first()
        )
        if assignment is None:
            return {key: False for key in STAFF_PERMISSION_KEYS}
        perms = assignment.permissions_dict
        return {
            'can_manage_business': False,
            'can_manage_shops': perms.get('can_manage_shop_profile', False),
            'can_manage_staff': perms.get('can_manage_employees', False),
            'can_manage_catalog': perms.get('can_manage_catalog', False),
            'can_view_reports': perms.get('can_view_analytics', False),
            'can_manage_orders': perms.get('can_manage_orders', False),
            **{key: bool(perms.get(key, False)) for key in STAFF_PERMISSION_KEYS},
        }

    return {
        'can_manage_business': False,
        'can_manage_shops': True,
        'can_manage_staff': False,
        'can_manage_catalog': True,
        'can_view_reports': False,
        'can_manage_orders': True,
    }


def build_session_payload(user, *, app_entry: str | None) -> dict[str, Any]:
    active_shop_id = None
    if app_entry == APP_ENTRY_STAFF:
        assignment = (
            ShopStaffAssignment.objects.filter(
                staff_member__user_id=user.id,
                staff_member__is_active=True,
                is_active=True,
            )
            .select_related('shop')
            .order_by('-updated_at')
            .first()
        )
        assignments_count = count_assigned_shops(user.id)
        if assignment and assignments_count == 1:
            active_shop_id = assignment.shop_id
        return {
            'active_shop_id': active_shop_id,
            'shops_count': count_active_shops(user.id),
            'assigned_shops_count': assignments_count,
        }

    shops_count = count_active_shops(user.id)
    if shops_count == 1:
        active_shop_id = (
            _active_shops_queryset(user.id)
            .order_by('-is_pinned', '-created_at')
            .values_list('id', flat=True)
            .first()
        )
    return {
        'active_shop_id': active_shop_id,
        'shops_count': shops_count,
        'assigned_shops_count': count_assigned_shops(user.id),
    }


def build_v2_me_payload(user, *, app_entry: str | None) -> dict[str, Any]:
    app_entry = normalize_v2_app_entry(app_entry)
    return {
        'app_entry': app_entry,
        'membership': build_membership_payload(user, app_entry=app_entry),
        'permissions': build_permissions_payload(user, app_entry=app_entry),
        'session': build_session_payload(user, app_entry=app_entry),
        'onboarding': build_onboarding_flags(user, app_entry=app_entry),
    }


def build_v2_verify_payload(
    user,
    *,
    app_entry: str | None,
    is_new_user: bool,
) -> dict[str, Any]:
    from apps.core.phone_utils import format_phone_for_display

    app_entry = validate_app_entry_for_user(user, app_entry)
    session = None
    if app_entry:
        session = TailorSession(
            shop_id=None,
            access_mode=(
                ACCESS_MODE_EMPLOYEE
                if app_entry == APP_ENTRY_STAFF
                else ACCESS_MODE_OWNER
            ),
            app_entry=app_entry,
        )
    refresh = issue_tailor_tokens(user, session=session)
    return {
        'tokens': tokens_payload(refresh),
        'user': {
            'id': user.id,
            'phone': format_phone_for_display(user.phone),
            'full_name': user.get_full_name() or None,
            'avatar_url': None,
            'language': getattr(user, 'language', None) or 'ar',
        },
        'app_entry': app_entry,
        'is_new_user': is_new_user,
    }


def build_v2_profile_payload(user) -> dict[str, Any]:
    from apps.core.phone_utils import format_phone_for_display

    return {
        'id': user.id,
        'phone': format_phone_for_display(user.phone),
        'full_name': user.get_full_name() or None,
        'avatar_url': None,
        'language': getattr(user, 'language', None) or 'ar',
    }


def switch_shop_session(user, shop_id: int, *, app_entry: str | None):
    session = resolve_shop_session(user, shop_id)
    session = TailorSession(
        shop_id=session.shop_id,
        access_mode=session.access_mode,
        app_entry=normalize_v2_app_entry(app_entry) if app_entry else session.app_entry,
    )
    refresh = issue_tailor_tokens(user, session=session)
    return {
        'tokens': {'access_token': str(refresh.access_token)},
        'session': {
            'active_shop_id': shop_id,
            'access_mode': session.access_mode,
            'app_entry': session.app_entry,
        },
    }
