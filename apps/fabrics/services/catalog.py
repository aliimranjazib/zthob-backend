"""Fabric product catalog queries and writes."""

from __future__ import annotations

from django.db import transaction
from rest_framework import serializers

from apps.fabrics.models import FabricProduct, ShopFabric
from apps.fabrics.services.legacy_bridge import sync_legacy_fabric_from_shop_fabric
from apps.fabrics.services.listings import assign_product_to_shop
from apps.tailors.services.v2.shops import active_shops_queryset, get_shop_for_owner


def sync_product_assignments_to_legacy(*, product: FabricProduct) -> None:
    for shop_fabric in product.shop_assignments.filter(is_active=True).select_related('shop'):
        sync_legacy_fabric_from_shop_fabric(shop_fabric=shop_fabric)


ASSIGN_FIELD_NAMES = ('shop_id', 'stock', 'price_override', 'is_visible')


def fabric_products_queryset(*, business_id: int):
    return (
        FabricProduct.objects.filter(business_id=business_id)
        .select_related('fabric_type', 'category', 'country', 'business', 'created_by')
        .prefetch_related('tags', 'gallery', 'shop_assignments__shop')
        .order_by('-created_at')
    )


def get_product_for_business(*, business_id: int, product_id: int) -> FabricProduct | None:
    return fabric_products_queryset(business_id=business_id).filter(id=product_id).first()


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

    sync_product_assignments_to_legacy(product=product)
    return product


def pop_product_assign_fields(validated_data: dict) -> tuple[dict, dict | None]:
    """Split create payload into product fields and optional shop assignment."""
    product_data = dict(validated_data)
    assign_data = {}
    for field in ASSIGN_FIELD_NAMES:
        if field in product_data:
            assign_data[field] = product_data.pop(field)

    if 'shop_id' not in assign_data and 'stock' not in assign_data:
        return product_data, None

    if assign_data.get('stock') is None:
        assign_data['stock'] = 0

    return product_data, assign_data


def resolve_shop_for_product_assignment(
    *,
    owner_id: int,
    business_id: int,
    shop_id: int | None,
):
    if shop_id is not None:
        shop = get_shop_for_owner(owner_id=owner_id, shop_id=shop_id)
        if shop is None or shop.business_id != business_id:
            return None
        return shop

    shops = list(active_shops_queryset(owner_id=owner_id, business_id=business_id)[:2])
    if len(shops) == 1:
        return shops[0]
    return None


@transaction.atomic
def assign_created_product_to_shop(
    *,
    product: FabricProduct,
    owner_id: int,
    assign_data: dict,
    created_by,
):
    shop = resolve_shop_for_product_assignment(
        owner_id=owner_id,
        business_id=product.business_id,
        shop_id=assign_data.get('shop_id'),
    )
    if shop is None:
        if assign_data.get('shop_id') is not None:
            raise serializers.ValidationError({'shop_id': 'Shop not found for this business.'})
        raise serializers.ValidationError(
            {'shop_id': 'shop_id is required when stock is provided and the business has multiple shops.'}
        )

    return assign_product_to_shop(
        product=product,
        shop=shop,
        stock=assign_data.get('stock', 0),
        price_override=assign_data.get('price_override'),
        is_visible=assign_data.get('is_visible', True),
        created_by=created_by,
    )
