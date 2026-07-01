# apps/tailors/permissions.py
from rest_framework import permissions

from apps.tailors.shop_access import user_can_manage_shop_order, user_can_record_shop_measurements


def _get_required_permissions(view):
    perms = getattr(view, 'required_employee_permissions', None)
    if perms:
        return tuple(perms)
    perm = getattr(view, 'required_employee_permission', None)
    return (perm,) if perm else ()


def _employee_has_view_permission(employee, view):
    required = _get_required_permissions(view)
    if not required:
        return True
    return any(getattr(employee, perm, False) for perm in required)


class IsTailor(permissions.BasePermission):
    """
    Allows access only to users with the role 'TAILOR'.
    """
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (user.is_tailor or user.is_admin))


class IsAdmin(permissions.BasePermission):
    """
    Allows access only to users with the role 'ADMIN'.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_admin)


class IsShopStaff(permissions.BasePermission):

    """
    Permission class to handle Access Control for Tailor Shop Owners and Employees.
    
    Logic:
    1. If user is the Owner of the shop profile: FULL ACCESS.
    2. If user is an Employee of the shop:
        - Must be 'is_active'.
        - Must be linked to the same shop (TailorProfile).
        - Must have the specific boolean permission flag set to True (if specified by view).
    """

    def has_permission(self, request, view):
        # Must be authenticated and have a professional role (TAILOR or ADMIN)
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_admin:
            return True

        if hasattr(request.user, 'tailor_employee'):
            employee = request.user.tailor_employee
            if not employee.is_active:
                return False

            return _employee_has_view_permission(employee, view)

        if hasattr(request.user, 'tailor_profile'):
            return True

        return False

    def has_object_permission(self, request, view, obj):
        """
        Ensures the staff member belongs to the correct shop when accessing specific objects 
        (like individual Orders or Fabrics).
        """
        from apps.orders.models import Order

        user = request.user

        # Order.tailor is a User id — compare via shop owner, not TailorProfile id.
        if isinstance(obj, Order):
            if user.is_admin:
                return True
            if hasattr(user, 'tailor_profile') and obj.tailor_id == user.id:
                return True
            if hasattr(user, 'tailor_employee'):
                employee = user.tailor_employee
                if not employee.is_active:
                    return False
                if getattr(view, 'allow_pos_measurements', False):
                    return user_can_record_shop_measurements(user, obj)
                required = _get_required_permissions(view)
                if not required:
                    return user_can_manage_shop_order(user, obj, employee_permission='can_manage_orders')
                return any(
                    user_can_manage_shop_order(user, obj, employee_permission=perm)
                    for perm in required
                )
            return False

        # Determine the target tailor_id from the object
        # (Handles Fabrics, Categories, etc. where tailor_id is TailorProfile id)
        target_tailor_id = None
        if hasattr(obj, 'tailor_id'):
            target_tailor_id = obj.tailor_id
        elif hasattr(obj, 'tailor'):
            target_tailor_id = obj.tailor.id
        elif hasattr(obj, 'user_id'):  # For profiles
            target_tailor_id = obj.id

        required_perm = getattr(view, 'required_employee_permission', None)

        # 1. Owner Check: Does this shop belong to the current user?
        if hasattr(user, 'tailor_profile') and user.id == target_tailor_id:
            return True

        # 2. Staff Check: Does this employee work for this specific shop?
        if hasattr(user, 'tailor_employee'):
            employee = user.tailor_employee
            if employee.is_active and employee.tailor_id == target_tailor_id:
                if required_perm:
                    return getattr(employee, required_perm, False)
                return _employee_has_view_permission(employee, view)

        return False
