def get_token_shop_id(request):
    """Read active shop id from JWT claims when present."""
    if request is None:
        return None

    token = getattr(request, 'auth', None)
    if token is None:
        return None

    shop_id = token.get('shop_id') if hasattr(token, 'get') else None
    if shop_id in (None, ''):
        return None
    try:
        return int(shop_id)
    except (TypeError, ValueError):
        return None


def user_owns_shop(user, shop) -> bool:
    if not user or not shop:
        return False
    if shop.owner_id == user.id:
        return True
    return bool(shop.user_id and shop.user_id == user.id)


def get_shop_staff_context(user, shop_id=None):
    """
    Active staff record for a shop session.

    Prefers owner roster assignments when ``shop_id`` is set, then falls back
    to legacy ``user.tailor_employee``.
    """
    if not user or not getattr(user, 'is_authenticated', False):
        return None

    if shop_id is not None:
        from apps.tailors.models import ShopStaffAssignment

        assignment = (
            ShopStaffAssignment.objects.filter(
                shop_id=shop_id,
                is_active=True,
                staff_member__is_active=True,
                staff_member__user_id=user.id,
            )
            .select_related('shop', 'staff_member', 'staff_member__user')
            .first()
        )
        if assignment:
            return assignment

    employee = getattr(user, 'tailor_employee', None)
    if employee and employee.is_active:
        if shop_id is None or employee.tailor_id == shop_id:
            return employee
    return None


def get_shop_staff_context_for_order(user, order):
    """Resolve staff permissions for an order's shop owner."""
    if not user or not order or not order.tailor_id:
        return get_shop_staff_context(user)

    from django.db.models import Q
    from apps.tailors.models import ShopStaffAssignment

    assignment = (
        ShopStaffAssignment.objects.filter(
            staff_member__user_id=user.id,
            staff_member__is_active=True,
            is_active=True,
        )
        .filter(
            Q(shop__owner_id=order.tailor_id)
            | Q(shop__user_id=order.tailor_id)
        )
        .select_related('shop', 'staff_member')
        .first()
    )
    if assignment:
        return assignment
    return get_shop_staff_context(user)


def get_user_shop_assignments(user):
    """All active shop assignments for owner/staff auth context."""
    from apps.tailors.models import ShopStaffAssignment

    return (
        ShopStaffAssignment.objects.filter(
            staff_member__user_id=user.id,
            staff_member__is_active=True,
            is_active=True,
        )
        .select_related('shop', 'staff_member')
        .order_by('-assigned_at')
    )


def get_tailor_profile(user, shop_id=None):
    """TailorProfile for owner or active employee shop session."""
    from apps.tailors.models import TailorProfile

    if shop_id is not None:
        try:
            shop = TailorProfile.objects.get(id=shop_id)
        except TailorProfile.DoesNotExist:
            return None

        if user_owns_shop(user, shop):
            return shop

        if get_shop_staff_context(user, shop_id=shop.id):
            return shop
        return None

    staff = get_shop_staff_context(user)
    if staff:
        return staff.tailor

    profile = getattr(user, 'tailor_profile', None)
    if profile:
        return profile

    return TailorProfile.objects.filter(owner=user).order_by('created_at').first()


def get_shop_owner_user(user, shop_id=None):
    """Owner User for this shop session (owner or employee's shop)."""
    profile = get_tailor_profile(user, shop_id=shop_id)
    return profile.shop_owner_user if profile else None


def shop_media_uploader_ids(user):
    """
    User IDs whose uploaded media this session may attach.

    Shop owner and active employees share photos uploaded by anyone in the shop.
    Customers and other roles may only use their own uploads.
    """
    if not user or not getattr(user, 'is_authenticated', False):
        return set()

    allowed = {user.id}
    owner = get_shop_owner_user(user)
    if owner is None:
        return allowed

    allowed.add(owner.id)
    from apps.tailors.models import TailorEmployee, ShopStaffAssignment
    allowed.update(
        TailorEmployee.objects.filter(
            tailor__owner_id=owner.id,
            is_active=True,
        ).values_list('user_id', flat=True)
    )
    allowed.update(
        ShopStaffAssignment.objects.filter(
            shop__owner_id=owner.id,
            is_active=True,
            staff_member__is_active=True,
        ).values_list('staff_member__user_id', flat=True)
    )
    return allowed


def user_can_manage_shop_order(user, order, *, employee_permission='can_manage_orders', shop_id=None):
    """
    True if user is the order's tailor owner OR an active employee
    of that shop with the given permission.
    """
    if not order or not order.tailor_id:
        return False

    owner_id = order.tailor_id

    if user.id == owner_id:
        return True

    staff = get_shop_staff_context(user, shop_id=shop_id)
    if not staff or not staff.is_active:
        return False
    if staff.tailor.shop_owner_user_id != owner_id:
        return False
    if employee_permission:
        return getattr(staff, employee_permission, False)
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
        employee = TailorEmployee.objects.select_related('user', 'tailor', 'tailor__owner').get(id=employee_id)
    except (TailorEmployee.DoesNotExist, TypeError, ValueError):
        raise ValueError("Assigned employee was not found.")

    if not employee.is_active:
        raise ValueError("Assigned employee is inactive.")
    if employee.tailor.shop_owner_user_id != shop_owner_user.id:
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

    staff = get_shop_staff_context_for_order(user, order)
    if not staff or not staff.is_active or not staff.can_stitch_orders:
        return False
    if staff.tailor.shop_owner_user_id != order.tailor_id:
        return False

    assigned = getattr(order, 'assigned_employee', None)
    if assigned is None:
        return True
    if hasattr(staff, 'staff_member'):
        return assigned.user_id == staff.user.id
    return assigned.id == staff.id


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

    if getattr(user, 'tailor_profile', None) and not get_shop_staff_context(user):
        return queryset

    staff = get_shop_staff_context(user)
    if not staff or not staff.is_active:
        return queryset

    if staff.can_manage_orders:
        return queryset

    if staff.can_stitch_orders:
        from apps.tailors.models import TailorEmployee

        legacy_employee = TailorEmployee.objects.filter(
            user_id=user.id,
            tailor_id=staff.tailor_id,
            is_active=True,
        ).first()
        if legacy_employee:
            return queryset.filter(
                Q(assigned_employee__isnull=True) | Q(assigned_employee=legacy_employee)
            )
        return queryset.filter(assigned_employee__isnull=True)

    return queryset
