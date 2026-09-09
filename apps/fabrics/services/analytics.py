"""Fabric catalog analytics."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db.models import Count, Sum
from django.db.models.functions import Coalesce

from apps.fabrics.models import ShopFabric
from apps.orders.models import OrderItem


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
