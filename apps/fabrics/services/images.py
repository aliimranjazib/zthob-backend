"""Shared fabric image validation and gallery helpers."""

from __future__ import annotations

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
