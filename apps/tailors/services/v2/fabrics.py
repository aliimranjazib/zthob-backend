"""V2 fabric catalog, branch stock, and analytics services."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Sum
from django.db.models.functions import Coalesce

from apps.orders.models import OrderItem
from apps.tailors.models import Fabric
from apps.tailors.models.v2_fabrics import FabricProduct, FabricStockMovement, ShopFabric


def fabric_products_queryset(*, business_id: int):
    return (
        FabricProduct.objects.filter(business_id=business_id)
        .select_related('fabric_type', 'category', 'country', 'business', 'created_by')
        .prefetch_related('tags', 'gallery', 'shop_assignments__shop')
        .order_by('-created_at')
    )


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
        .prefetch_related('product__tags', 'product__gallery')
        .order_by('-created_at')
    )


def get_product_for_business(*, business_id: int, product_id: int) -> FabricProduct | None:
    return fabric_products_queryset(business_id=business_id).filter(id=product_id).first()


def get_shop_fabric(*, shop_id: int, shop_fabric_id: int) -> ShopFabric | None:
    return shop_fabrics_queryset(shop_id=shop_id).filter(id=shop_fabric_id).first()


def _legacy_is_active(*, shop_fabric: ShopFabric) -> bool:
    product = shop_fabric.product
    return bool(
        shop_fabric.is_active
        and shop_fabric.is_visible
        and product.is_active
        and product.approval_status == 'approved'
    )


def sync_legacy_fabric_from_shop_fabric(*, shop_fabric: ShopFabric) -> Fabric:
    product = shop_fabric.product
    shop = shop_fabric.shop
    price = shop_fabric.effective_price

    if shop_fabric.legacy_fabric_id:
        fabric = shop_fabric.legacy_fabric
    else:
        fabric = Fabric(tailor=shop)

    fabric.name = product.name
    fabric.description = product.description
    fabric.price = price
    fabric.stitching_price = product.stitching_price
    fabric.stock = shop_fabric.stock
    fabric.seasons = product.seasons
    fabric.approval_status = product.approval_status
    fabric.is_active = _legacy_is_active(shop_fabric=shop_fabric)
    fabric.fabric_type = product.fabric_type
    fabric.category = product.category
    fabric.country = product.country
    fabric.save()

    fabric.tags.set(product.tags.all())

    if shop_fabric.legacy_fabric_id != fabric.id:
        shop_fabric.legacy_fabric = fabric
        shop_fabric.save(update_fields=['legacy_fabric', 'updated_at'])

    return fabric


@transaction.atomic
def create_fabric_product(*, business, validated_data, created_by) -> FabricProduct:
    tags = validated_data.pop('tags', None)
    product = FabricProduct.objects.create(
        business=business,
        created_by=created_by,
        **validated_data,
    )
    if tags is not None:
        product.tags.set(tags)
    return product


@transaction.atomic
def update_fabric_product(*, product: FabricProduct, validated_data) -> FabricProduct:
    tags = validated_data.pop('tags', None)
    for field, value in validated_data.items():
        setattr(product, field, value)
    product.save()
    if tags is not None:
        product.tags.set(tags)

    for shop_fabric in ShopFabric.objects.filter(product=product, is_active=True).select_related('shop'):
        sync_legacy_fabric_from_shop_fabric(shop_fabric=shop_fabric)
    return product


@transaction.atomic
def assign_product_to_shop(
    *,
    product: FabricProduct,
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


def record_sale_from_legacy_fabric(
    *,
    fabric: Fabric,
    quantity: int,
    order_id: int | None = None,
    user=None,
) -> None:
    shop_fabric = getattr(fabric, 'v2_shop_fabric', None)
    if shop_fabric is None:
        return

    previous_stock = shop_fabric.stock
    new_stock = fabric.stock
    if previous_stock == new_stock:
        return

    shop_fabric.stock = new_stock
    shop_fabric.save(update_fields=['stock', 'updated_at'])

    FabricStockMovement.objects.create(
        shop_fabric=shop_fabric,
        movement_type=FabricStockMovement.TYPE_SALE,
        quantity=quantity,
        previous_stock=previous_stock,
        new_stock=new_stock,
        reason='order',
        order_id=order_id,
        created_by=user,
    )


def _order_items_for_analytics(
    *,
    business_id: int,
    shop_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
):
    qs = OrderItem.objects.filter(
        fabric__isnull=False,
        fabric__v2_shop_fabric__product__business_id=business_id,
    ).exclude(order__status='cancelled')

    if shop_id is not None:
        qs = qs.filter(fabric__v2_shop_fabric__shop_id=shop_id)
    if date_from is not None:
        qs = qs.filter(order__created_at__date__gte=date_from)
    if date_to is not None:
        qs = qs.filter(order__created_at__date__lte=date_to)
    return qs


def get_fabric_analytics(
    *,
    business_id: int,
    shop_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    low_stock_threshold: int = 5,
):
    order_items = _order_items_for_analytics(
        business_id=business_id,
        shop_id=shop_id,
        date_from=date_from,
        date_to=date_to,
    )

    summary = order_items.aggregate(
        total_units_sold=Coalesce(Sum('quantity'), 0),
        total_revenue=Coalesce(Sum('total_price'), Decimal('0.00')),
        total_orders=Count('order_id', distinct=True),
    )

    by_product = list(
        order_items.values(
            'fabric__v2_shop_fabric__product_id',
            'fabric__v2_shop_fabric__product__name',
            'fabric__v2_shop_fabric__product__sku',
        )
        .annotate(
            units_sold=Coalesce(Sum('quantity'), 0),
            revenue=Coalesce(Sum('total_price'), Decimal('0.00')),
            order_count=Count('order_id', distinct=True),
        )
        .order_by('-units_sold')
    )
    for row in by_product:
        row['product_id'] = row.pop('fabric__v2_shop_fabric__product_id')
        row['product_name'] = row.pop('fabric__v2_shop_fabric__product__name')
        row['product_sku'] = row.pop('fabric__v2_shop_fabric__product__sku')

    by_shop = list(
        order_items.values(
            'fabric__v2_shop_fabric__shop_id',
            'fabric__v2_shop_fabric__shop__shop_name',
        )
        .annotate(
            units_sold=Coalesce(Sum('quantity'), 0),
            revenue=Coalesce(Sum('total_price'), Decimal('0.00')),
            order_count=Count('order_id', distinct=True),
        )
        .order_by('-units_sold')
    )
    for row in by_shop:
        row['shop_id'] = row.pop('fabric__v2_shop_fabric__shop_id')
        row['shop_name'] = row.pop('fabric__v2_shop_fabric__shop__shop_name')

    low_stock_qs = ShopFabric.objects.filter(
        product__business_id=business_id,
        is_active=True,
    ).select_related('product', 'shop', 'legacy_fabric')
    if shop_id is not None:
        low_stock_qs = low_stock_qs.filter(shop_id=shop_id)
    low_stock = [
        {
            'shop_fabric_id': sf.id,
            'shop_id': sf.shop_id,
            'shop_name': sf.shop.shop_name,
            'product_id': sf.product_id,
            'product_name': sf.product.name,
            'product_sku': sf.product.sku,
            'stock': sf.stock,
            'available_stock': sf.available_stock,
            'legacy_fabric_id': sf.legacy_fabric_id,
        }
        for sf in low_stock_qs.filter(stock__lte=low_stock_threshold).order_by('stock', 'product__name')
    ]

    return {
        'summary': summary,
        'by_product': by_product,
        'by_shop': by_shop,
        'low_stock': low_stock,
        'filters': {
            'shop_id': shop_id,
            'date_from': date_from.isoformat() if date_from else None,
            'date_to': date_to.isoformat() if date_to else None,
            'low_stock_threshold': low_stock_threshold,
        },
    }
