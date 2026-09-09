"""V2 staff query helpers."""

from __future__ import annotations

from apps.tailors.models import TailorStaffMember


def staff_roster_queryset(*, owner_id: int):
    return (
        TailorStaffMember.objects.filter(owner_id=owner_id)
        .select_related('user')
        .prefetch_related('shop_assignments__shop')
        .order_by('-joined_at')
    )


def get_staff_member(*, owner_id: int, staff_id: int) -> TailorStaffMember | None:
    return (
        staff_roster_queryset(owner_id=owner_id)
        .filter(id=staff_id)
        .first()
    )
