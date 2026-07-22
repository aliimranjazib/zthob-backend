"""Helpers for style preset reference images."""

import copy

from apps.orders.style_references import (
    format_reference_image_urls,
    resolve_reference_image_ids,
    resolve_stored_reference_image_paths,
)


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


def format_preset_styles_for_response(styles, request=None):
    """Return preset styles with CORS-friendly reference image URLs."""
    if not styles:
        return []

    processed = copy.deepcopy(styles)
    if not request:
        return processed

    for style in processed:
        reference_paths = resolve_stored_reference_image_paths(style)
        style.pop('reference_image_ids', None)
        style['reference_images'] = format_reference_image_urls(reference_paths, request)

    return processed
