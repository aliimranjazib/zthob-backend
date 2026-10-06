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


class RequiresOwnerPlatformSession(permissions.BasePermission):
    """
    Owner console APIs require JWT app_entry=owner (re-auth with owner verify).

    Header-only app_entry is not sufficient — prevents solo tailor sessions
    from using owner/shops, staff, orders, and reports routes.
    """

    message = 'Owner console requires an owner app session. Sign in with app_entry=owner.'

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_admin:
            return True
        from apps.accounts.services.session_app_entry import has_owner_platform_jwt

        return has_owner_platform_jwt(request)
