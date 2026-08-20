"""Helpers for customer-provided fabric photos on stitching-only orders."""

from rest_framework import serializers

from apps.core.media_utils import build_public_media_url
from apps.orders.models import CustomerFabricImage

MAX_CUSTOMER_FABRIC_IMAGES = 4
MAX_CUSTOMER_FABRIC_IMAGE_BYTES = 5 * 1024 * 1024


def resolve_customer_fabric_image_ids(image_ids, user, item_index):
    """Validate ownership and unused status, then return IDs in request order."""
    field_name = f'items[{item_index}].customer_fabric_image_ids'

    if image_ids is None:
        return []

    if not isinstance(image_ids, list):
        raise serializers.ValidationError({field_name: 'Must be an array of image IDs.'})

    if not image_ids:
        return []

    if len(image_ids) > MAX_CUSTOMER_FABRIC_IMAGES:
        raise serializers.ValidationError({
            field_name: f'Maximum {MAX_CUSTOMER_FABRIC_IMAGES} fabric images allowed per item.',
        })

    normalized_ids = []
    for image_id in image_ids:
        if not isinstance(image_id, int):
            raise serializers.ValidationError({field_name: 'Each fabric image ID must be an integer.'})
        normalized_ids.append(image_id)

    if len(set(normalized_ids)) != len(normalized_ids):
        raise serializers.ValidationError({field_name: 'Duplicate fabric image IDs are not allowed.'})

    if user is None or not getattr(user, 'is_authenticated', False):
        raise serializers.ValidationError({
            field_name: 'Authentication is required to attach fabric images.',
        })

    images = CustomerFabricImage.objects.filter(
        id__in=normalized_ids,
        uploaded_by=user,
        order_item__isnull=True,
    )
    images_by_id = {image.id: image for image in images}
    missing_ids = [image_id for image_id in normalized_ids if image_id not in images_by_id]
    if missing_ids:
        raise serializers.ValidationError({
            field_name: f'Invalid, already used, or unauthorized fabric image IDs: {missing_ids}',
        })

    return normalized_ids


def attach_customer_fabric_images(*, order_item, image_ids, user):
    """Lock unused photos and attach them to the order item in request order."""
    if not image_ids:
        return

    locked = list(
        CustomerFabricImage.objects.select_for_update().filter(
            id__in=image_ids,
            uploaded_by=user,
            order_item__isnull=True,
        )
    )
    by_id = {image.id: image for image in locked}
    missing_ids = [image_id for image_id in image_ids if image_id not in by_id]
    if missing_ids:
        raise serializers.ValidationError({
            'items': f'Customer fabric image IDs are invalid or already used: {missing_ids}',
        })

    for display_order, image_id in enumerate(image_ids):
        image = by_id[image_id]
        image.order_item = order_item
        image.display_order = display_order
        image.save(update_fields=['order_item', 'display_order', 'updated_at'])


def format_customer_fabric_images(item, request=None):
    """Return public URLs for customer fabric photos attached to an order item."""
    images = getattr(item, 'customer_fabric_images', None)
    if images is None:
        return []

    payload = []
    for image in images.all():
        if not image.image:
            continue
        payload.append({
            'id': image.id,
            'path': image.image.name,
            'url': build_public_media_url(request, image.image.url),
        })
    return payload
