"""Permission classes for account and owner-app endpoints."""

from rest_framework import permissions


class IsOwnerAppUser(permissions.BasePermission):
    """
    Users allowed to use owner-app account endpoints.

    Includes shop owners, staff with shop assignments, and tailors/admins.
    Blocks unrelated customer-only accounts from owner profile routes.
    """

    message = 'Owner app access requires a tailor account or shop assignment.'

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_admin or user.is_tailor:
            return True

        from apps.tailors.models import ShopStaffAssignment, TailorProfile

        if TailorProfile.objects.filter(owner=user).exists():
            return True

        return ShopStaffAssignment.objects.filter(
            staff_member__user_id=user.id,
            staff_member__is_active=True,
            is_active=True,
        ).exists()
