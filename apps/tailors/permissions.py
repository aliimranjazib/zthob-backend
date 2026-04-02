# apps/tailors/permissions.py
from rest_framework import permissions


class IsTailor(permissions.BasePermission):
    """
    Allows access only to users with the role 'TAILOR'.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'TAILOR')


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
            
        if request.user.role not in ['TAILOR', 'ADMIN']:
            return False

        # Allow if User is an Owner (has tailor_profile)
        if hasattr(request.user, 'tailor_profile'):
            return True

        # Allow if User is an Employee (has tailor_employee)
        if hasattr(request.user, 'tailor_employee'):
            employee = request.user.tailor_employee
            if not employee.is_active:
                return False
            
            # Check for specific permission flag (if defined in the view)
            required_perm = getattr(view, 'required_employee_permission', None)
            if required_perm:
                return getattr(employee, required_perm, False)
            
            # If no specific permission required, just being an active staff member is enough for basic access
            return True

        return False

    def has_object_permission(self, request, view, obj):
        """
        Ensures the staff member belongs to the correct shop when accessing specific objects 
        (like individual Orders or Fabrics).
        """
        user = request.user
        
        # Determine the target tailor_id from the object
        # (Handles Orders, Fabrics, Categories, etc.)
        target_tailor_id = None
        if hasattr(obj, 'tailor_id'):
            target_tailor_id = obj.tailor_id
        elif hasattr(obj, 'tailor'):
            target_tailor_id = obj.tailor.id
        elif hasattr(obj, 'user_id'): # For profiles
             target_tailor_id = obj.id

        # 1. Owner Check: Does this shop belong to the current user?
        if hasattr(user, 'tailor_profile') and user.tailor_profile.id == target_tailor_id:
            return True

        # 2. Staff Check: Does this employee work for this specific shop?
        if hasattr(user, 'tailor_employee'):
            employee = user.tailor_employee
            if employee.is_active and employee.tailor_id == target_tailor_id:
                # Permission flag check (same logic as has_permission)
                required_perm = getattr(view, 'required_employee_permission', None)
                if required_perm:
                    return getattr(employee, required_perm, False)
                return True

        return False