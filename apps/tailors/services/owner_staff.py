"""Shared helpers for owner staff roster management."""

from __future__ import annotations

from django.db import transaction

from apps.core.services import PhoneVerificationService


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

    with transaction.atomic():
        assignment, created = ShopStaffAssignment.objects.get_or_create(
            staff_member=staff_member,
            shop=shop,
            defaults={'roles': roles or []},
        )
        assignment.apply_roles_and_permissions(roles, permissions)
        assignment.is_active = is_active
        assignment.save()
        sync_legacy_employee_from_assignment(assignment)
    return assignment, created
