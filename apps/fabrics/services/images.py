"""Shared fabric image validation and gallery helpers."""

from __future__ import annotations

from dataclasses import dataclass

from rest_framework import serializers

from apps.fabrics.models import FabricProduct, FabricProductImage


ALLOWED_IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png']
MAX_IMAGES = 4
MAX_IMAGE_BYTES = 5 * 1024 * 1024


def parse_multipart_images(request) -> list[dict]:
    """Parse v1-compatible indexed multipart image keys from a request."""
    images_data = []
    index = 0
    while True:
        image_key = f'images[{index}][image]'
        is_primary_key = f'images[{index}][is_primary]'
        order_key = f'images[{index}][order]'

        if image_key in request.FILES:
            images_data.append(
                {
                    'image': request.FILES[image_key],
                    'is_primary': request.POST.get(is_primary_key, 'false').lower() == 'true',
                    'order': int(request.POST.get(order_key, '0')),
                }
            )
            index += 1
        else:
            break

    if not images_data and getattr(request, 'FILES', None):
        single = request.FILES.get('image')
        if single is not None:
            images_data.append(
                {
                    'image': single,
                    'is_primary': request.POST.get('is_primary', 'false').lower() == 'true',
                    'order': int(request.POST.get('order', '0')),
                }
            )
    return images_data


def validate_gallery_images(images: list[dict], *, required: bool = False) -> list[dict]:
    if required and not images:
        raise serializers.ValidationError({'images': 'At least one image must be provided'})

    if len(images) > MAX_IMAGES:
        raise serializers.ValidationError({'images': f'Maximum {MAX_IMAGES} images are allowed per fabric'})

    primary_images = [img for img in images if img.get('is_primary', False)]
    if len(primary_images) > 1:
        raise serializers.ValidationError({'images': 'Only one image can be marked as primary'})
    if images and not primary_images:
        images[0]['is_primary'] = True

    orders = [img.get('order', 0) for img in images]
    if len(set(orders)) != len(orders):
        for idx, img in enumerate(images):
            img['order'] = idx

    for img in images:
        image = img.get('image')
        if image is None:
            raise serializers.ValidationError({'images': 'Each image entry must include a file'})
        if image.size > MAX_IMAGE_BYTES:
            raise serializers.ValidationError({'images': f'Image size exceeds 5MB limit: {image.name}'})
        extension = image.name.rsplit('.', 1)[-1].lower()
        if extension not in ALLOWED_IMAGE_EXTENSIONS:
            raise serializers.ValidationError(
                {'images': f'Invalid file format for {image.name}. Only JPG, JPEG, and PNG files are allowed.'}
            )

    return images


def save_product_gallery(*, product: FabricProduct, images: list[dict]) -> None:
    for img_data in sorted(images, key=lambda item: item.get('order', 0)):
        FabricProductImage.objects.create(
            product=product,
            image=img_data['image'],
            is_primary=img_data.get('is_primary', False),
            order=img_data.get('order', 0),
        )


def add_product_gallery_images(*, product: FabricProduct, images: list[dict]) -> None:
    current_count = product.gallery.count()
    if current_count + len(images) > MAX_IMAGES:
        raise serializers.ValidationError(
            {'images': f'Maximum {MAX_IMAGES} images are allowed per fabric product'}
        )

    if any(img.get('is_primary') for img in images):
        product.gallery.filter(is_primary=True).update(is_primary=False)

    save_product_gallery(product=product, images=images)


def delete_product_image(*, product: FabricProduct, image: FabricProductImage) -> None:
    if product.gallery.count() <= 1:
        raise serializers.ValidationError({'images': 'Cannot delete the last image of a fabric product'})

    was_primary = image.is_primary
    image.delete()

    if was_primary:
        replacement = product.gallery.order_by('order', 'id').first()
        if replacement:
            replacement.is_primary = True
            replacement.save()


def append_product_gallery_from_request(*, product: FabricProduct, request) -> list[dict]:
    """Parse multipart images from a request and append them to the product gallery."""
    images = parse_multipart_images(request)
    if not images:
        return []
    validate_gallery_images(images, required=False)
    add_product_gallery_images(product=product, images=images)
    return images


def update_product_image(
    *,
    image: FabricProductImage,
    image_file=None,
    is_primary: bool | None = None,
    order: int | None = None,
) -> FabricProductImage:
    if image_file is not None:
        if image_file.size > MAX_IMAGE_BYTES:
            raise serializers.ValidationError({'image': f'Image size exceeds 5MB limit: {image_file.name}'})
        extension = image_file.name.rsplit('.', 1)[-1].lower()
        if extension not in ALLOWED_IMAGE_EXTENSIONS:
            raise serializers.ValidationError(
                {'image': f'Invalid file format for {image_file.name}. Only JPG, JPEG, and PNG files are allowed.'}
            )
        image.image = image_file

    if is_primary is not None:
        image.is_primary = is_primary
    if order is not None:
        image.order = order
    image.save()
    return image


@dataclass(frozen=True)
class ResolvedGalleryImage:
    """Gallery row the tailor app may address by id (legacy or V2 product image)."""

    kind: str
    fabric: object
    legacy_image: object | None = None
    product_image: FabricProductImage | None = None


def resolve_manageable_gallery_image(*, image_id: int, shop_profile_id: int) -> ResolvedGalleryImage | None:
    """
    Resolve an image id for v1 tailor gallery routes.

    Flutter often sends FabricProductImage ids from GET /v2/shops/.../fabrics/ while
    calling PATCH /tailors/images/<id>/update/ (legacy route).
    """
    from apps.fabrics.models import ShopFabric
    from apps.tailors.models import FabricImage

    legacy_image = (
        FabricImage.objects.filter(pk=image_id)
        .select_related('fabric', 'fabric__tailor')
        .first()
    )
    if legacy_image and legacy_image.fabric.tailor_id == shop_profile_id:
        return ResolvedGalleryImage(
            kind='legacy',
            fabric=legacy_image.fabric,
            legacy_image=legacy_image,
            product_image=None,
        )

    product_image = (
        FabricProductImage.objects.filter(pk=image_id)
        .select_related('product')
        .first()
    )
    if product_image is None:
        return None

    shop_fabric = (
        ShopFabric.objects.filter(
            product_id=product_image.product_id,
            shop_id=shop_profile_id,
            is_active=True,
        )
        .select_related('legacy_fabric', 'shop')
        .first()
    )
    if shop_fabric is None:
        return None

    fabric = shop_fabric.legacy_fabric
    if fabric is None:
        from apps.fabrics.services.legacy_bridge import sync_legacy_fabric_from_shop_fabric

        fabric = sync_legacy_fabric_from_shop_fabric(shop_fabric=shop_fabric)

    return ResolvedGalleryImage(
        kind='v2',
        fabric=fabric,
        legacy_image=None,
        product_image=product_image,
    )


def sync_galleries_after_product_image_change(*, product: FabricProduct) -> None:
    from apps.fabrics.services.catalog import sync_product_assignments_to_legacy

    sync_product_assignments_to_legacy(product=product)


def sync_galleries_after_legacy_image_change(*, fabric) -> None:
    from apps.fabrics.models import ShopFabric
    from apps.fabrics.services.legacy_bridge import sync_v2_from_legacy_fabric

    if ShopFabric.objects.filter(legacy_fabric_id=fabric.id, is_active=True).exists():
        sync_v2_from_legacy_fabric(fabric=fabric)
