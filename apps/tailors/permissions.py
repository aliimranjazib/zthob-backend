from rest_framework.permissions import BasePermission


class IsTailor(BasePermission):
    def has_permission(self, request, view):
        user=request.user
        print('DEBUG role:', getattr(request.user, 'role', None))
        return bool(user and user.is_authenticated and getattr(user, 'role', None) == 'TAILOR')