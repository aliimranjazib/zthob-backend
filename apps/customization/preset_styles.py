"""Helpers for style preset reference images."""

import copy

from apps.core.media_utils import build_public_media_url
from apps.orders.models import StyleReferenceImage
from apps.orders.style_references import resolve_reference_image_ids


def enrich_preset_style(style, idx, user):
    """Validate preset style selection and attach reference image paths."""
    reference_image_ids = style.get('reference_image_ids')
    if reference_image_ids is None:
        return style

    paths = resolve_reference_image_ids(reference_image_ids, user, idx)
    enriched = dict(style)
    enriched.pop('reference_image_ids', None)
    if paths is not None:
        enriched['reference_images'] = paths
    return enriched


def _resolve_legacy_reference_paths(style):
    """Best-effort lookup when presets stored ids without paths."""
    reference_image_ids = style.get('reference_image_ids')
    if not reference_image_ids or style.get('reference_images'):
        return style.get('reference_images') or []

    images = StyleReferenceImage.objects.filter(id__in=reference_image_ids)
    images_by_id = {image.id: image.image.name for image in images if image.image}
    return [
        images_by_id[image_id]
        for image_id in reference_image_ids
        if image_id in images_by_id
    ]


def format_preset_styles_for_response(styles, request=None):
    """Return preset styles with CORS-friendly reference image URLs."""
    if not styles:
        return []

    processed = copy.deepcopy(styles)
    if not request:
        return processed

    for style in processed:
        reference_paths = style.get('reference_images') or _resolve_legacy_reference_paths(style)
        style.pop('reference_image_ids', None)
        if reference_paths:
            style['reference_images'] = [
                build_public_media_url(request, image_path)
                for image_path in reference_paths
                if image_path
            ]
        elif 'reference_images' in style:
            style['reference_images'] = []

    return processed
