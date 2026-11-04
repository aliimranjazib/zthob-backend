"""Fabric product catalog queries and writes."""

from __future__ import annotations

from django.db import transaction

from apps.fabrics.models import FabricProduct
from apps.fabrics.services.fabric_names import (
    validate_fabric_name_for_business_owner_catalog,
    validate_fabric_name_for_shop,
)
from apps.fabrics.services.legacy_bridge import sync_legacy_fabric_from_shop_fabric


def sync_product_assignments_to_legacy(*, product: FabricProduct) -> None:
    for shop_fabric in product.shop_assignments.filter(is_active=True).select_related('shop'):
        sync_legacy_fabric_from_shop_fabric(shop_fabric=shop_fabric)


def fabric_products_queryset(*, business_id: int):
    return (
        FabricProduct.objects.filter(business_id=business_id)
        .select_related('fabric_type', 'category', 'country', 'business', 'created_by')
        .prefetch_related('tags', 'gallery', 'shop_assignments__shop')
        .order_by('-created_at')
    )


def owner_catalog_products_queryset(*, business_id: int):
    return fabric_products_queryset(business_id=business_id).filter(show_in_owner_catalog=True)


def get_product_for_business(*, business_id: int, product_id: int) -> FabricProduct | None:
    return fabric_products_queryset(business_id=business_id).filter(id=product_id).first()


def get_owner_catalog_product_for_business(*, business_id: int, product_id: int) -> FabricProduct | None:
    return owner_catalog_products_queryset(business_id=business_id).filter(id=product_id).first()


def _validate_product_name_rules(
    *,
    business_id: int,
    name: str | None,
    show_in_owner_catalog: bool,
    shop_id: int | None = None,
    exclude_product_id: int | None = None,
) -> None:
    if show_in_owner_catalog:
        validate_fabric_name_for_business_owner_catalog(
            business_id,
            name,
            exclude_product_id=exclude_product_id,
        )
    if shop_id is not None:
        validate_fabric_name_for_shop(
            shop_id,
            name,
            exclude_product_id=exclude_product_id,
        )


@transaction.atomic
def create_fabric_product(
    *,
    business,
    validated_data,
    created_by,
    shop_id: int | None = None,
) -> FabricProduct:
    show_in_owner_catalog = validated_data.get('show_in_owner_catalog', True)
    _validate_product_name_rules(
        business_id=business.id,
        name=validated_data.get('name'),
        show_in_owner_catalog=show_in_owner_catalog,
        shop_id=shop_id,
    )

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
    next_name = validated_data.get('name', product.name)
    next_show_in_owner = validated_data.get(
        'show_in_owner_catalog',
        product.show_in_owner_catalog,
    )
    name_changed = 'name' in validated_data
    catalog_flag_changed = 'show_in_owner_catalog' in validated_data
    if name_changed or catalog_flag_changed:
        _validate_product_name_rules(
            business_id=product.business_id,
            name=next_name,
            show_in_owner_catalog=next_show_in_owner,
            exclude_product_id=product.id,
        )
        if name_changed:
            for assignment in product.shop_assignments.filter(is_active=True):
                validate_fabric_name_for_shop(
                    assignment.shop_id,
                    next_name,
                    exclude_product_id=product.id,
                )

    for field, value in validated_data.items():
        setattr(product, field, value)
    product.save()
    if tags is not None:
        product.tags.set(tags)

    sync_product_assignments_to_legacy(product=product)
    return product
