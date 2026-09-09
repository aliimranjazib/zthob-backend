"""Sync V2 shop listings to legacy v1 Fabric rows for orders/checkout."""

from __future__ import annotations

from django.db import transaction
from rest_framework import serializers

from apps.fabrics.models import FabricProduct, FabricProductImage, ShopFabric
from apps.tailors.models import Fabric, FabricImage, FabricTag
from apps.tailors.shop_access import get_tailor_profile


def _legacy_is_active(*, shop_fabric: ShopFabric) -> bool:
    product = shop_fabric.product
    return bool(
        shop_fabric.is_active
        and shop_fabric.is_visible
        and product.is_active
        and product.approval_status == 'approved'
    )


def sync_legacy_fabric_images(*, product: FabricProduct, fabric: Fabric) -> None:
    """Mirror product gallery images onto the legacy fabric row."""
    product_images = list(product.gallery.all().order_by('-is_primary', 'order', 'id'))
    fabric.gallery.all().delete()
    for product_image in product_images:
        FabricImage.objects.create(
            fabric=fabric,
            image=product_image.image,
            is_primary=product_image.is_primary,
            order=product_image.order,
        )


@transaction.atomic
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
    fabric.is_on_sale = product.is_on_sale
    fabric.discount_price = product.discount_price
    fabric.sale_start = product.sale_start
    fabric.sale_end = product.sale_end
    fabric.is_featured = product.is_featured
    fabric.save()

    fabric.tags.set(product.tags.all())
    sync_legacy_fabric_images(product=product, fabric=fabric)

    if shop_fabric.legacy_fabric_id != fabric.id:
        shop_fabric.legacy_fabric = fabric
        shop_fabric.save(update_fields=['legacy_fabric', 'updated_at'])

    return fabric


@transaction.atomic
def create_from_v1_multipart(*, request, validated_data) -> Fabric:
    """Create a legacy fabric from v1 multipart payload and optionally link V2 catalog."""
    tailor_profile = get_tailor_profile(request.user)
    if not tailor_profile:
        raise serializers.ValidationError('Tailor shop profile not found.')

    images_data = validated_data.pop('images', [])
    tags_data = validated_data.pop('tags', [])

    fabric = Fabric.objects.create(
        tailor=tailor_profile,
        created_by=request.user,
        approval_status='approved',
        **validated_data,
    )

    if tags_data:
        tags = FabricTag.objects.filter(id__in=tags_data, is_active=True)
        fabric.tags.set(tags)

    for img_data in sorted(images_data, key=lambda item: item.get('order', 0)):
        FabricImage.objects.create(
            fabric=fabric,
            image=img_data['image'],
            is_primary=img_data.get('is_primary', False),
            order=img_data.get('order', 0),
        )

    link_legacy_fabric_to_business_catalog(fabric=fabric)
    return fabric


@transaction.atomic
def update_from_v1(*, fabric: Fabric, validated_data) -> Fabric:
    """Update legacy fabric from v1 payload and sync linked V2 rows when present."""
    tags_data = validated_data.pop('tags', None)

    for attr, value in validated_data.items():
        setattr(fabric, attr, value)
    fabric.approval_status = 'approved'
    fabric.save()

    if tags_data is not None:
        tags = FabricTag.objects.filter(id__in=tags_data, is_active=True)
        fabric.tags.set(tags)

    sync_v2_from_legacy_fabric(fabric=fabric)
    return fabric


@transaction.atomic
def sync_v2_from_legacy_fabric(*, fabric: Fabric) -> None:
    """Mirror v1 fabric changes onto linked business catalog rows."""
    if not hasattr(fabric, 'v2_shop_fabric'):
        return

    shop_fabric = fabric.v2_shop_fabric
    product = shop_fabric.product
    product.name = fabric.name
    product.description = fabric.description
    product.price = fabric.price
    product.stitching_price = fabric.stitching_price
    product.seasons = fabric.seasons
    product.approval_status = fabric.approval_status
    product.is_active = fabric.is_active
    product.is_on_sale = fabric.is_on_sale
    product.discount_price = fabric.discount_price
    product.sale_start = fabric.sale_start
    product.sale_end = fabric.sale_end
    product.is_featured = fabric.is_featured
    product.fabric_type = fabric.fabric_type
    product.category = fabric.category
    product.country = fabric.country
    product.save()
    product.tags.set(fabric.tags.all())

    product.gallery.all().delete()
    for legacy_image in fabric.gallery.all().order_by('-is_primary', 'order', 'id'):
        FabricProductImage.objects.create(
            product=product,
            image=legacy_image.image,
            is_primary=legacy_image.is_primary,
            order=legacy_image.order,
        )

    shop_fabric.stock = fabric.stock
    shop_fabric.is_visible = fabric.is_active
    shop_fabric.save(update_fields=['stock', 'is_visible', 'updated_at'])
    sync_legacy_fabric_from_shop_fabric(shop_fabric=shop_fabric)


@transaction.atomic
def link_legacy_fabric_to_business_catalog(*, fabric: Fabric) -> ShopFabric | None:
    """Optional back-link when v1 creates a fabric for a shop that belongs to a business."""
    shop = fabric.tailor
    business_id = getattr(shop, 'business_id', None)
    if not business_id:
        return None

    if hasattr(fabric, 'v2_shop_fabric'):
        return fabric.v2_shop_fabric

    product = FabricProduct.objects.create(
        business_id=business_id,
        name=fabric.name,
        description=fabric.description,
        price=fabric.price,
        stitching_price=fabric.stitching_price,
        seasons=fabric.seasons,
        approval_status=fabric.approval_status,
        is_active=fabric.is_active,
        is_on_sale=fabric.is_on_sale,
        discount_price=fabric.discount_price,
        sale_start=fabric.sale_start,
        sale_end=fabric.sale_end,
        is_featured=fabric.is_featured,
        fabric_type=fabric.fabric_type,
        category=fabric.category,
        country=fabric.country,
        created_by=fabric.created_by,
    )
    if fabric.tags.exists():
        product.tags.set(fabric.tags.all())

    for legacy_image in fabric.gallery.all():
        FabricProductImage.objects.create(
            product=product,
            image=legacy_image.image,
            is_primary=legacy_image.is_primary,
            order=legacy_image.order,
        )

    shop_fabric = ShopFabric.objects.create(
        shop=shop,
        product=product,
        legacy_fabric=fabric,
        stock=fabric.stock,
        is_visible=fabric.is_active,
        is_active=True,
        created_by=fabric.created_by,
    )
    return shop_fabric
