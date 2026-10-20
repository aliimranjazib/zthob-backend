"""Test helpers for promised Tailor Plus / Owner Plus gates."""

from apps.tailors.models import BusinessOwnerPlusSubscription, ShopTailorPlusSubscription


def grant_shop_plus(shop):
    ShopTailorPlusSubscription.objects.get_or_create(
        shop=shop,
        defaults={'status': ShopTailorPlusSubscription.STATUS_ACTIVE},
    )
    return shop


def grant_owner_plus(business):
    BusinessOwnerPlusSubscription.objects.get_or_create(
        business=business,
        defaults={'status': BusinessOwnerPlusSubscription.STATUS_ACTIVE},
    )
    return business
