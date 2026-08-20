"""Helpers for style preset reference images."""

import copy

from apps.orders.style_references import (
    format_style_reference_fields,
    resolve_reference_image_ids,
)


def enrich_preset_style(style, idx, user, customer=None):
    """Validate preset style selection and attach reference image paths."""
    reference_image_ids = style.get('reference_image_ids')
    if reference_image_ids is None:
        return style

    paths = resolve_reference_image_ids(reference_image_ids, user, idx, customer=customer)
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
        reference_urls, reference_image_ids = format_style_reference_fields(style, request)
        style['reference_images'] = reference_urls
        style['reference_image_ids'] = reference_image_ids

    return processed
