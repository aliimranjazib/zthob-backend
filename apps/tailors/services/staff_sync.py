"""Sync owner staff assignments with legacy TailorEmployee records."""

from __future__ import annotations

from apps.tailors.models import TailorEmployee
from apps.tailors.models.staff import STAFF_PERMISSION_KEYS, ShopStaffAssignment


def apply_permissions(employee, permissions_list):
    for key in STAFF_PERMISSION_KEYS:
        setattr(employee, key, key in (permissions_list or []))


def sync_legacy_employee_from_assignment(assignment: ShopStaffAssignment):
    """
    Keep legacy ``TailorEmployee`` in sync for the assignment's shop.

    Legacy tailor app still reads ``user.tailor_employee`` for single-shop flows.
    """
    staff_member = assignment.staff_member
    user = staff_member.user
    shop = assignment.shop

    existing = getattr(user, 'tailor_employee', None)
    if existing and existing.tailor_id != shop.id:
        return existing

    employee, _created = TailorEmployee.objects.get_or_create(
        tailor=shop,
        user=user,
        defaults={'roles': assignment.roles or []},
    )
    employee.roles = assignment.roles or []
    employee.is_active = bool(
        assignment.is_active and staff_member.is_active
    )
    apply_permissions(employee, [
        key for key in STAFF_PERMISSION_KEYS if getattr(assignment, key, False)
    ])
    employee.save()
    return employee


def deactivate_legacy_employee_for_assignment(assignment: ShopStaffAssignment):
    """Deactivate legacy employee row when assignment is removed or deactivated."""
    TailorEmployee.objects.filter(
        tailor_id=assignment.shop_id,
        user_id=assignment.staff_member.user_id,
    ).update(is_active=False)
