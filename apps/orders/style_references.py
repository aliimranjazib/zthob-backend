"""Helpers for style reference image uploads and custom_styles enrichment."""

from rest_framework import serializers

from apps.orders.models import StyleReferenceImage

MAX_STYLE_REFERENCE_IMAGES = 4
MAX_STYLE_REFERENCE_IMAGE_BYTES = 5 * 1024 * 1024


def resolve_reference_image_ids(reference_image_ids, user, style_index):
    """Validate ownership and return relative media paths in request order."""
    if reference_image_ids is None:
        return None

    field_name = f'custom_styles[{style_index}].reference_image_ids'

    if not isinstance(reference_image_ids, list):
        raise serializers.ValidationError({field_name: 'Must be an array of image IDs.'})

    if not reference_image_ids:
        return []

    if len(reference_image_ids) > MAX_STYLE_REFERENCE_IMAGES:
        raise serializers.ValidationError({
            field_name: f'Maximum {MAX_STYLE_REFERENCE_IMAGES} reference images allowed per style.',
        })

    normalized_ids = []
    for image_id in reference_image_ids:
        if not isinstance(image_id, int):
            raise serializers.ValidationError({field_name: 'Each reference image ID must be an integer.'})
        normalized_ids.append(image_id)

    if len(set(normalized_ids)) != len(normalized_ids):
        raise serializers.ValidationError({field_name: 'Duplicate reference image IDs are not allowed.'})

    if user is None or not getattr(user, 'is_authenticated', False):
        raise serializers.ValidationError({field_name: 'Authentication is required to attach reference images.'})

    images = StyleReferenceImage.objects.filter(id__in=normalized_ids, uploaded_by=user)
    images_by_id = {image.id: image for image in images}
    missing_ids = [image_id for image_id in normalized_ids if image_id not in images_by_id]
    if missing_ids:
        raise serializers.ValidationError({
            field_name: f'Invalid or unauthorized reference image IDs: {missing_ids}',
        })

    return [images_by_id[image_id].image.name for image_id in normalized_ids]


def apply_reference_images_to_style(style_dict, reference_image_ids, user, style_index):
    """Attach validated reference image paths to an enriched style dict."""
    resolved_paths = resolve_reference_image_ids(reference_image_ids, user, style_index)
    if resolved_paths is not None:
        style_dict['reference_images'] = resolved_paths
    return style_dict
