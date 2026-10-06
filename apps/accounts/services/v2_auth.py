"""V2 authentication and session helpers."""

from __future__ import annotations

from typing import Any

from django.core.exceptions import PermissionDenied
from rest_framework import serializers

from apps.accounts.services.tailor_auth import (
    APP_ENTRY_OWNER,
    APP_ENTRY_STAFF,
    ACCESS_MODE_EMPLOYEE,
    ACCESS_MODE_OWNER,
    TailorSession,
    build_owner_auth_context,
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

TAILOR_SOLO_PERMISSIONS = {
    'can_manage_business': False,
    'can_manage_shops': True,
    'can_manage_staff': False,
    'can_manage_catalog': True,
    'can_view_reports': False,
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


def _user_has_staff_platform_access(user) -> bool:
    if ShopStaffAssignment.objects.filter(
        staff_member__user_id=user.id,
        staff_member__is_active=True,
        is_active=True,
    ).exists():
        return True
    employee = getattr(user, 'tailor_employee', None)
    return bool(employee and employee.is_active)


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


ACCOUNT_STATUS_NEW = 'new'
ACCOUNT_STATUS_EXISTING = 'existing'


def _user_has_platform_identity(user) -> bool:
    if Business.objects.filter(owner_id=user.id, is_active=True).exists():
        return True
    if _active_shops_queryset(user.id).exists():
        return True
    if ShopStaffAssignment.objects.filter(
        staff_member__user_id=user.id,
        staff_member__is_active=True,
        is_active=True,
    ).exists():
        return True
    if getattr(user, 'tailor_profile', None) is not None:
        return True
    return False


def resolve_v2_account_status(phone: str) -> str:
    """Return new vs existing before OTP based on platform identity for the phone."""
    from django.contrib.auth import get_user_model

    from apps.core.services import PhoneVerificationService

    User = get_user_model()
    if not phone:
        return ACCOUNT_STATUS_NEW

    local_phone = PhoneVerificationService.normalize_phone_to_local(phone)
    user = User.objects.filter(phone=local_phone).first()
    if user is None:
        return ACCOUNT_STATUS_NEW
    if _user_has_platform_identity(user):
        return ACCOUNT_STATUS_EXISTING
    return ACCOUNT_STATUS_NEW


def infer_app_entry_for_user(user) -> str:
    membership_type = resolve_membership_type(user)
    if membership_type == 'owner':
        return APP_ENTRY_OWNER
    if membership_type == 'staff':
        return APP_ENTRY_STAFF
    if membership_type == 'tailor':
        return APP_ENTRY_TAILOR
    raise serializers.ValidationError(
        {'app_entry': 'app_entry is required for new registration.'}
    )


def resolve_v2_app_entry(
    user,
    *,
    requested_app_entry: str | None,
    membership_before: str,
) -> tuple[str, str]:
    """
    Resolve session app_entry from explicit request or platform identity.

    Returns (app_entry, app_entry_source) where source is 'request' or 'inferred'.
    """
    if requested_app_entry not in (None, ''):
        app_entry = validate_app_entry_for_user(user, requested_app_entry)
        return app_entry, 'request'

    if membership_before != 'none':
        app_entry = infer_app_entry_for_user(user)
        app_entry = validate_app_entry_for_user(user, app_entry)
        return app_entry, 'inferred'

    raise serializers.ValidationError(
        {'app_entry': 'app_entry is required for new registration.'}
    )


def validate_app_entry_for_user(user, app_entry: str | None) -> str | None:
    app_entry = normalize_v2_app_entry(app_entry)
    if app_entry is None:
        return None

    membership_type = resolve_membership_type(user)
    if app_entry == APP_ENTRY_OWNER:
        if membership_type == 'staff' and not _active_shops_queryset(user.id).exists():
            return APP_ENTRY_STAFF
        return app_entry
    if app_entry == APP_ENTRY_STAFF:
        if membership_type == 'owner':
            return app_entry
        if membership_type == 'staff' or _user_has_staff_platform_access(user):
            return app_entry
        raise PermissionDenied('This account is not assigned as staff.')
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


def resolve_membership_type_for_app_entry(user, app_entry: str | None) -> str:
    """
    Membership type for the current session (request app_entry), not platform identity alone.
    """
    app_entry = normalize_v2_app_entry(app_entry)
    if app_entry == APP_ENTRY_TAILOR:
        return 'tailor'
    if app_entry == APP_ENTRY_STAFF:
        if resolve_membership_type(user) == 'staff':
            return 'staff'
        return 'staff'
    if app_entry == APP_ENTRY_OWNER:
        identity = resolve_membership_type(user)
        if identity == 'owner':
            return 'owner'
        if identity == 'staff':
            return 'staff'
        return 'owner'
    return resolve_membership_type(user)


def user_owns_active_shop(user) -> bool:
    return _active_shops_queryset(user.id).exists()


def build_platform_payload(
    user,
    *,
    app_entry: str | None,
    token_app_entry: str | None = None,
) -> dict[str, Any]:
    app_entry = normalize_v2_app_entry(app_entry)
    token_entry = (token_app_entry or '').strip().lower() or None
    return {
        'entry': app_entry,
        'owns_shop': user_owns_active_shop(user),
        'owner_console_enabled': token_entry == APP_ENTRY_OWNER,
    }


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
    membership_type = resolve_membership_type_for_app_entry(user, app_entry)

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
    app_entry = normalize_v2_app_entry(app_entry)

    if app_entry == APP_ENTRY_OWNER:
        if resolve_membership_type_for_app_entry(user, app_entry) == 'owner':
            return dict(OWNER_PERMISSIONS)
        return dict(TAILOR_SOLO_PERMISSIONS)

    if app_entry == APP_ENTRY_STAFF:
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

    return dict(TAILOR_SOLO_PERMISSIONS)


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


def build_v2_me_payload(
    user,
    *,
    app_entry: str | None,
    token_app_entry: str | None = None,
) -> dict[str, Any]:
    app_entry = normalize_v2_app_entry(app_entry)
    payload = {
        'app_entry': app_entry,
        'membership': build_membership_payload(user, app_entry=app_entry),
        'permissions': build_permissions_payload(user, app_entry=app_entry),
        'session': build_session_payload(user, app_entry=app_entry),
        'onboarding': build_onboarding_flags(user, app_entry=app_entry),
        'platform': build_platform_payload(
            user,
            app_entry=app_entry,
            token_app_entry=token_app_entry,
        ),
    }
    if app_entry in (APP_ENTRY_OWNER, APP_ENTRY_STAFF):
        payload['tailor_context'] = build_owner_auth_context(
            user,
            app_entry=app_entry,
        )
    return payload


def build_v2_verify_payload(
    user,
    *,
    app_entry: str | None,
    is_new_user: bool,
    app_entry_source: str = 'request',
) -> dict[str, Any]:
    from apps.core.phone_utils import format_phone_for_display

    session = None
    tailor_context = None
    if app_entry:
        session_info = build_session_payload(user, app_entry=app_entry)
        active_shop_id = session_info.get('active_shop_id')
        shop_id = (
            active_shop_id
            if app_entry == APP_ENTRY_STAFF and active_shop_id
            else None
        )
        session = TailorSession(
            shop_id=shop_id,
            access_mode=(
                ACCESS_MODE_EMPLOYEE
                if app_entry == APP_ENTRY_STAFF
                else ACCESS_MODE_OWNER
            ),
            app_entry=app_entry,
        )
        if app_entry in (APP_ENTRY_OWNER, APP_ENTRY_STAFF):
            tailor_context = build_owner_auth_context(
                user,
                app_entry=app_entry,
                active_shop_id=shop_id,
            )
    refresh = issue_tailor_tokens(user, session=session)
    payload = {
        'tokens': tokens_payload(refresh),
        'user': {
            'id': user.id,
            'phone': format_phone_for_display(user.phone),
            'full_name': user.get_full_name() or None,
            'avatar_url': None,
            'language': getattr(user, 'language', None) or 'ar',
        },
        'app_entry': app_entry,
        'app_entry_source': app_entry_source,
        'is_new_user': is_new_user,
    }
    if tailor_context is not None:
        payload['tailor_context'] = tailor_context
    return payload


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
    resolved = resolve_shop_session(user, shop_id)
    effective_entry = (
        normalize_v2_app_entry(app_entry)
        if app_entry
        else (
            APP_ENTRY_STAFF
            if resolved.access_mode == ACCESS_MODE_EMPLOYEE
            else APP_ENTRY_OWNER
        )
    )
    session = TailorSession(
        shop_id=resolved.shop_id,
        access_mode=resolved.access_mode,
        app_entry=effective_entry,
    )
    refresh = issue_tailor_tokens(user, session=session)
    tailor_context = build_owner_auth_context(
        user,
        app_entry=effective_entry,
        active_shop_id=shop_id,
    )
    tailor_context['access_mode'] = session.access_mode
    return {
        'tokens': {'access_token': str(refresh.access_token)},
        'session': {
            'active_shop_id': shop_id,
            'access_mode': session.access_mode,
            'app_entry': session.app_entry,
        },
        'tailor_context': tailor_context,
    }
