"""Keep shop listings, legacy fabrics, and customer catalog in sync on remove/delete."""

from __future__ import annotations

from django.db import transaction

from apps.fabrics.models import ShopFabric
from apps.fabrics.services.legacy_bridge import sync_legacy_fabric_from_shop_fabric
from apps.tailors.models import Fabric


def shop_listing_is_live(*, shop_fabric: ShopFabric) -> bool:
    from apps.fabrics.services.legacy_bridge import _legacy_is_active

    return _legacy_is_active(shop_fabric=shop_fabric)


@transaction.atomic
def deactivate_shop_listing(*, shop_fabric: ShopFabric) -> ShopFabric:
    """Remove a fabric from the shop shelf and hide it from customers."""
    shop_fabric.is_active = False
    shop_fabric.is_visible = False
    shop_fabric.save(update_fields=['is_active', 'is_visible', 'updated_at'])
    sync_legacy_fabric_from_shop_fabric(shop_fabric=shop_fabric)
    return shop_fabric


@transaction.atomic
def detach_product_from_shop(*, product_id: int, shop_id: int) -> bool:
    shop_fabric = (
        ShopFabric.objects.filter(product_id=product_id, shop_id=shop_id)
        .select_related('product', 'shop', 'legacy_fabric')
        .first()
    )
    if shop_fabric is None:
        return False
    deactivate_shop_listing(shop_fabric=shop_fabric)
    return True


@transaction.atomic
def deactivate_product_shop_assignments(*, product) -> int:
    count = 0
    for shop_fabric in product.shop_assignments.filter(is_active=True).select_related(
        'shop',
        'legacy_fabric',
    ):
        deactivate_shop_listing(shop_fabric=shop_fabric)
        count += 1
    return count


@transaction.atomic
def delete_tailor_fabric(*, fabric: Fabric) -> None:
    """
    Permanently delete a legacy fabric and deactivate any linked v2 shop listing
    so sync will not recreate a customer-visible row.
    """
    shop_fabric = (
        ShopFabric.objects.filter(legacy_fabric_id=fabric.id)
        .select_related('product', 'shop', 'legacy_fabric')
        .first()
    )
    if shop_fabric is not None:
        deactivate_shop_listing(shop_fabric=shop_fabric)
    fabric.delete()


@transaction.atomic
def deactivate_tailor_fabric(*, fabric: Fabric) -> Fabric:
    """Soft-remove: hide from customers and shop inventory without deleting the row."""
    shop_fabric = (
        ShopFabric.objects.filter(legacy_fabric_id=fabric.id)
        .select_related('product', 'shop', 'legacy_fabric')
        .first()
    )
    if shop_fabric is not None:
        deactivate_shop_listing(shop_fabric=shop_fabric)
    elif hasattr(fabric, 'v2_shop_fabric'):
        try:
            deactivate_shop_listing(shop_fabric=fabric.v2_shop_fabric)
        except ShopFabric.DoesNotExist:
            pass
    fabric.is_active = False
    fabric.save(update_fields=['is_active', 'updated_at'])
    return fabric
