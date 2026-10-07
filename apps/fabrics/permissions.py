"""Shared permission helpers for fabric endpoints."""

from apps.accounts.services.session_app_entry import has_owner_platform_jwt
from apps.tailors.models import TailorProfile
from apps.tailors.shop_access import (
    get_shop_staff_context_for_request,
    get_token_shop_id,
    user_owns_shop,
)


def _user_owns_any_active_shop(user) -> bool:
    return (
        TailorProfile.objects.filter(owner=user)
        .exclude(shop_name__isnull=True)
        .exclude(shop_name='')
        .exists()
    )


def staff_has_fabric_permission(request, permission_key: str) -> bool:
    user = request.user
    if user.is_admin:
        return True
    if has_owner_platform_jwt(request):
        return True
    staff = get_shop_staff_context_for_request(request)
    if staff and staff.is_active:
        return bool(getattr(staff, permission_key, False))
    token_shop_id = get_token_shop_id(request)
    if token_shop_id is not None:
        shop = TailorProfile.objects.filter(id=token_shop_id).first()
        if shop and user_owns_shop(user, shop):
            return True
    if _user_owns_any_active_shop(user):
        return True
    return False


def user_can_manage_shop_fabrics(request, *, shop_id: int) -> bool:
    user = request.user
    if user.is_admin:
        return True
    if has_owner_platform_jwt(request):
        from apps.tailors.services.v2.shops import get_shop_for_owner

        shop = get_shop_for_owner(owner_id=user.id, shop_id=shop_id)
        return shop is not None

    try:
        shop = TailorProfile.objects.get(id=shop_id)
    except TailorProfile.DoesNotExist:
        return False
    if user_owns_shop(user, shop):
        return True

    staff = get_shop_staff_context_for_request(request, shop_id=shop_id)
    if staff and staff.is_active and staff.shop_id == shop_id:
        return bool(staff.can_manage_catalog)
    return False
