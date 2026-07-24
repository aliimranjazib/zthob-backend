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
    if user_can_record_shop_measurements(user, order):
        return True
    return user_can_see_stitch_order(user, order)


def user_is_pos_only_for_order(user, order):
    """Walk-in shop staff with POS permission but not full order management."""
    if not order or order.service_mode != 'walk_in':
        return False
    if user_can_manage_shop_order(user, order, employee_permission='can_manage_orders'):
        return False
    return user_can_manage_shop_order(user, order, employee_permission='can_manage_pos')


def order_supports_employee_stitch_assignment(order):
    """Orders that involve stitching can have an assigned shop employee."""
    if not order:
        return False
    return order.order_type in ('fabric_with_stitching', 'stitching_only')


def resolve_assignable_stitch_employee(shop_owner_user, employee_id):
    """
    Resolve a TailorEmployee id that may be assigned to stitch for this shop.
    Raises ValueError with a user-facing message on failure.
    """
    from apps.tailors.models import TailorEmployee

    if not shop_owner_user:
        raise ValueError("Shop owner is required to assign an employee.")

    try:
        employee = TailorEmployee.objects.select_related('user', 'tailor').get(id=employee_id)
    except (TailorEmployee.DoesNotExist, TypeError, ValueError):
        raise ValueError("Assigned employee was not found.")

    if not employee.is_active:
        raise ValueError("Assigned employee is inactive.")
    if employee.tailor.user_id != shop_owner_user.id:
        raise ValueError("Assigned employee does not belong to this shop.")
    if not employee.can_stitch_orders:
        raise ValueError("This employee is not enabled for stitching assignments.")

    return employee


def user_can_see_stitch_order(user, order):
    """
    Rider-style visibility for stitching:

    - Owner / can_manage_orders → always
    - Assigned employee → only that employee (among stitchers)
    - Unassigned (open) → any employee with can_stitch_orders
    """
    if not order or not order.tailor_id:
        return False

    if user.id == order.tailor_id:
        return True

    if user_can_manage_shop_order(user, order, employee_permission='can_manage_orders'):
        return True

    employee = getattr(user, 'tailor_employee', None)
    if not employee or not employee.is_active or not employee.can_stitch_orders:
        return False
    if employee.tailor.user_id != order.tailor_id:
        return False

    assigned = getattr(order, 'assigned_employee', None)
    if assigned is None:
        return True
    return assigned.id == employee.id


def user_can_perform_order_stitching(user, order):
    """
    Who may run start/finish/mark_ready stitching actions.

    Same open-vs-assigned rules as visibility.
    """
    return user_can_see_stitch_order(user, order)


def filter_orders_for_shop_staff(queryset, user):
    """
    Narrow shop order lists for the current staff user.

    Owners and can_manage_orders staff see all shop orders.
    Stitch-only staff see open jobs + their assigned jobs.
    """
    from django.db.models import Q

    if not user:
        return queryset.none()

    if getattr(user, 'tailor_profile', None) and not getattr(user, 'tailor_employee', None):
        return queryset

    employee = getattr(user, 'tailor_employee', None)
    if not employee or not employee.is_active:
        return queryset

    if employee.can_manage_orders:
        return queryset

    if employee.can_stitch_orders:
        return queryset.filter(
            Q(assigned_employee__isnull=True) | Q(assigned_employee=employee)
        )

    return queryset
