from rest_framework.permissions import BasePermission


class IsRider(BasePermission):
    """Permission class to check if user is a rider"""
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and getattr(user, 'role', None) == 'RIDER')
