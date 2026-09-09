"""Shared permission helpers for fabric endpoints."""

from apps.tailors.services.v2.business import get_owner_business
from apps.tailors.shop_access import get_shop_staff_context


def staff_has_fabric_permission(request, permission_key: str) -> bool:
    user = request.user
    if user.is_admin:
        return True
    if get_owner_business(user) is not None:
        return True
    staff = get_shop_staff_context(request)
    if staff and staff.is_active:
        return bool(getattr(staff, permission_key, False))
    return False


def user_can_manage_shop_fabrics(request, *, shop_id: int) -> bool:
    if staff_has_fabric_permission(request, 'can_manage_catalog'):
        staff = get_shop_staff_context(request, shop_id=shop_id)
        if staff and staff.is_active and staff.shop_id == shop_id:
            return True
    business = get_owner_business(request.user)
    if business is None:
        return False
    from apps.tailors.services.v2.shops import get_shop_for_owner

    shop = get_shop_for_owner(owner_id=request.user.id, shop_id=shop_id)
    return shop is not None and shop.business_id == business.id
