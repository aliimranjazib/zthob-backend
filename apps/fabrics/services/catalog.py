"""Fabric product catalog queries and writes."""

from __future__ import annotations

from django.db import transaction

from apps.fabrics.models import FabricProduct, ShopFabric


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
    from apps.fabrics.services.legacy_bridge import sync_legacy_fabric_from_shop_fabric

    tags = validated_data.pop('tags', None)
    for field, value in validated_data.items():
        setattr(product, field, value)
    product.save()
    if tags is not None:
        product.tags.set(tags)

    for shop_fabric in ShopFabric.objects.filter(product=product, is_active=True).select_related('shop'):
        sync_legacy_fabric_from_shop_fabric(shop_fabric=shop_fabric)
    return product
