"""Shared helpers for owner staff roster management."""

from __future__ import annotations

from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.core.services import PhoneVerificationService
from apps.tailors.models.employee import TailorEmployee

ROLE_DEFAULT_PERMISSIONS: dict[str, list[str]] = {
    TailorEmployee.ROLE_MANAGER: [
        'can_manage_orders',
        'can_manage_catalog',
        'can_view_analytics',
        'can_manage_pos',
        'can_manage_shop_profile',
        'can_manage_shop_status',
        'can_manage_shop_address',
        'can_stitch_orders',
    ],
    TailorEmployee.ROLE_STITCHER: [
        'can_manage_orders',
        'can_stitch_orders',
    ],
    TailorEmployee.ROLE_CUTTER: [
        'can_manage_orders',
        'can_manage_catalog',
        'can_stitch_orders',
    ],
    TailorEmployee.ROLE_RECEPTIONIST: [
        'can_manage_orders',
        'can_manage_pos',
    ],
    TailorEmployee.ROLE_FINISHER: [
        'can_manage_orders',
        'can_stitch_orders',
    ],
}


def find_or_create_staff_user(*, phone: str, name: str):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    phone = PhoneVerificationService.normalize_phone_to_local(phone)
    name = (name or '').strip()
    name_parts = name.split(' ', 1)

    user = User.objects.filter(phone=phone).first()
    if not user:
        username = f'emp_{phone}'
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f'emp_{phone}_{counter}'
            counter += 1
        user = User.objects.create_user(
            username=username,
            phone=phone,
            first_name=name_parts[0] if name_parts else '',
            last_name=name_parts[1] if len(name_parts) > 1 else '',
            email=None,
            role='TAILOR',
            is_active=True,
        )
        return user, True

    user.first_name = name_parts[0] if name_parts else user.first_name
    user.last_name = name_parts[1] if len(name_parts) > 1 else user.last_name
    if user.is_customer and not user.is_tailor and not user.is_admin:
        from apps.accounts.services.identity import IdentityService
        IdentityService.ensure_profile(user, 'TAILOR')
        user.role = 'TAILOR'
    user.save(update_fields=['first_name', 'last_name', 'role'])
    return user, False


def resolve_permissions_for_roles(roles, permissions):
    """Merge explicit permissions with defaults for each role when none provided."""
    explicit = list(permissions or [])
    if explicit:
        return explicit
    merged: list[str] = []
    for role in roles or []:
        for key in ROLE_DEFAULT_PERMISSIONS.get(role, []):
            if key not in merged:
                merged.append(key)
    return merged


def assert_single_manager_per_shop(
    shop,
    roles,
    *,
    is_active=True,
    exclude_assignment_id=None,
):
    if not is_active:
        return
    if TailorEmployee.ROLE_MANAGER not in (roles or []):
        return

    from apps.tailors.models import ShopStaffAssignment

    qs = ShopStaffAssignment.objects.filter(
        shop_id=shop.id,
        is_active=True,
        staff_member__is_active=True,
    )
    if exclude_assignment_id is not None:
        qs = qs.exclude(pk=exclude_assignment_id)

    for other in qs.only('id', 'roles'):
        if TailorEmployee.ROLE_MANAGER in (other.roles or []):
            raise ValidationError(
                {'roles': 'This shop already has an active manager.'}
            )


def sync_shop_contact_for_manager(assignment):
    if not assignment.is_active or not assignment.staff_member.is_active:
        return
    if TailorEmployee.ROLE_MANAGER not in (assignment.roles or []):
        return

    user = assignment.staff_member.user
    phone = (user.phone or '').strip()
    if not phone:
        return

    shop = assignment.shop
    shop.contact_number = phone
    shop.save(update_fields=['contact_number'])


def create_or_update_shop_assignment(
    *,
    staff_member,
    shop,
    roles,
    permissions,
    is_active=True,
):
    from apps.tailors.models import ShopStaffAssignment
    from apps.tailors.services.staff_sync import sync_legacy_employee_from_assignment

    roles = list(roles or [])
    permissions = resolve_permissions_for_roles(roles, permissions)

    with transaction.atomic():
        assignment, created = ShopStaffAssignment.objects.get_or_create(
            staff_member=staff_member,
            shop=shop,
            defaults={'roles': roles},
        )
        assert_single_manager_per_shop(
            shop,
            roles,
            is_active=is_active,
            exclude_assignment_id=assignment.pk,
        )
        assignment.apply_roles_and_permissions(roles, permissions)
        assignment.is_active = is_active
        assignment.save()
        sync_shop_contact_for_manager(assignment)
        sync_legacy_employee_from_assignment(assignment)
    return assignment, created
