def get_tailor_profile(user):
    """TailorProfile for owner or active employee shop session."""
    from apps.tailors.models import TailorProfile

    employee = getattr(user, 'tailor_employee', None)
    if employee and employee.is_active:
        return employee.tailor

    profile = getattr(user, 'tailor_profile', None)
    if profile:
        return profile

    return TailorProfile.objects.filter(user=user).first()


def get_shop_owner_user(user):
    """Owner User for this shop session (owner or employee's shop)."""
    profile = get_tailor_profile(user)
    return profile.user if profile else None


def user_can_manage_shop_order(user, order, *, employee_permission='can_manage_orders'):
    """
    True if user is the order's tailor owner OR an active employee
    of that shop with the given permission.
    """
    if not order or not order.tailor_id:
        return False

    owner_id = order.tailor_id

    if user.id == owner_id:
        return True

    employee = getattr(user, 'tailor_employee', None)
    if not employee or not employee.is_active:
        return False
    if employee.tailor.user_id != owner_id:
        return False
    if employee_permission:
        return getattr(employee, employee_permission, False)
    return True

def user_can_record_shop_measurements(user, order):
    """Walk-in shop measurements for order managers or POS staff."""
    if not order or order.service_mode != 'walk_in':
        return False
    return (
        user_can_manage_shop_order(user, order, employee_permission='can_manage_orders')
        or user_can_manage_shop_order(user, order, employee_permission='can_manage_pos')
    )


def user_has_tailor_order_visibility(user, order):
    """Show tailor-side transitions/actions for order managers or walk-in POS staff."""
    if user_can_manage_shop_order(user, order, employee_permission='can_manage_orders'):
        return True
    return user_can_record_shop_measurements(user, order)


def user_is_pos_only_for_order(user, order):
    """Walk-in shop staff with POS permission but not full order management."""
    if not order or order.service_mode != 'walk_in':
        return False
    if user_can_manage_shop_order(user, order, employee_permission='can_manage_orders'):
        return False
    return user_can_manage_shop_order(user, order, employee_permission='can_manage_pos')