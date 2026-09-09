"""Shop fabric listing queries and updates."""

from __future__ import annotations

from django.db import transaction

from apps.fabrics.models import FabricStockMovement, ShopFabric
from apps.fabrics.services.legacy_bridge import sync_legacy_fabric_from_shop_fabric


def shop_fabrics_queryset(*, shop_id: int):
    return (
        ShopFabric.objects.filter(shop_id=shop_id, is_active=True)
        .select_related(
            'shop',
            'product',
            'product__fabric_type',
            'product__category',
            'product__country',
            'legacy_fabric',
        )
        .prefetch_related('product__tags', 'product__gallery', 'product__shop_assignments')
        .order_by('-created_at')
    )


def get_shop_fabric(*, shop_id: int, shop_fabric_id: int) -> ShopFabric | None:
    return shop_fabrics_queryset(shop_id=shop_id).filter(id=shop_fabric_id).first()


@transaction.atomic
def assign_product_to_shop(
    *,
    product,
    shop,
    stock: int,
    price_override=None,
    is_visible: bool = True,
    created_by=None,
) -> ShopFabric:
    shop_fabric = ShopFabric.objects.filter(shop=shop, product=product).first()
    previous_stock = shop_fabric.stock if shop_fabric else 0

    if shop_fabric is None:
        shop_fabric = ShopFabric.objects.create(
            shop=shop,
            product=product,
            stock=stock,
            price_override=price_override,
            is_visible=is_visible,
            is_active=True,
            created_by=created_by,
        )
        movement_type = FabricStockMovement.TYPE_ASSIGN
    else:
        shop_fabric.stock = stock
        shop_fabric.price_override = price_override
        shop_fabric.is_visible = is_visible
        shop_fabric.is_active = True
        shop_fabric.save(
            update_fields=[
                'stock',
                'price_override',
                'is_visible',
                'is_active',
                'updated_at',
            ]
        )
        movement_type = FabricStockMovement.TYPE_ADJUSTMENT_SET

    sync_legacy_fabric_from_shop_fabric(shop_fabric=shop_fabric)

    FabricStockMovement.objects.create(
        shop_fabric=shop_fabric,
        movement_type=movement_type,
        quantity=stock - previous_stock,
        previous_stock=previous_stock,
        new_stock=shop_fabric.stock,
        reason='assign',
        created_by=created_by,
    )
    return shop_fabric


@transaction.atomic
def update_shop_fabric(*, shop_fabric: ShopFabric, validated_data) -> ShopFabric:
    stock_changed = 'stock' in validated_data
    previous_stock = shop_fabric.stock

    for field, value in validated_data.items():
        setattr(shop_fabric, field, value)
    shop_fabric.save()

    if stock_changed and shop_fabric.stock != previous_stock:
        FabricStockMovement.objects.create(
            shop_fabric=shop_fabric,
            movement_type=FabricStockMovement.TYPE_ADJUSTMENT_SET,
            quantity=shop_fabric.stock - previous_stock,
            previous_stock=previous_stock,
            new_stock=shop_fabric.stock,
            reason='update',
        )

    sync_legacy_fabric_from_shop_fabric(shop_fabric=shop_fabric)
    return shop_fabric


@transaction.atomic
def record_stock_movement(
    *,
    shop_fabric: ShopFabric,
    movement_type: str,
    quantity: int,
    reason: str = '',
    note: str = '',
    created_by=None,
    order_id: int | None = None,
) -> ShopFabric:
    previous_stock = shop_fabric.stock

    if movement_type == FabricStockMovement.TYPE_ADJUSTMENT_ADD:
        new_stock = previous_stock + quantity
    elif movement_type == FabricStockMovement.TYPE_ADJUSTMENT_REMOVE:
        new_stock = max(previous_stock - quantity, 0)
    elif movement_type == FabricStockMovement.TYPE_ADJUSTMENT_SET:
        new_stock = max(quantity, 0)
        quantity = new_stock - previous_stock
    elif movement_type == FabricStockMovement.TYPE_SALE:
        new_stock = max(previous_stock - quantity, 0)
    else:
        raise ValueError(f'Unsupported movement type: {movement_type}')

    shop_fabric.stock = new_stock
    shop_fabric.save(update_fields=['stock', 'updated_at'])

    if shop_fabric.legacy_fabric_id:
        legacy = shop_fabric.legacy_fabric
        legacy.stock = new_stock
        legacy.save(update_fields=['stock'])

    FabricStockMovement.objects.create(
        shop_fabric=shop_fabric,
        movement_type=movement_type,
        quantity=quantity,
        previous_stock=previous_stock,
        new_stock=new_stock,
        reason=reason,
        note=note,
        order_id=order_id,
        created_by=created_by,
    )
    return shop_fabric
