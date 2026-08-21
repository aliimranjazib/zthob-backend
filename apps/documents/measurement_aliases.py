"""Map legacy measurement JSON keys to thobe/PDF grid canonical field names.

Orders created before the thobe template often store keys like ``hem`` and
``tall_back``. The PDF grid is configured with thobe keys like
``sleeve_width`` and ``back_length``. This module resolves values across both.
"""

from apps.customization.thobe_grid import THOBE_FIELD_ORDER

# Legacy app keys (measurements_template) -> thobe canonical keys used on the PDF grid.
LEGACY_TO_CANONICAL = {
    'hem': 'sleeve_width',
    'tall_front': 'front_length',
    'tall_back': 'back_length',
    'armpit': 'armhole',
    'sleeve': 'plain_sleeve',
    'standard_hand': 'plain_sleeve',
    'cufflink': 'cuff_sleeve',
    'chest_upper': 'upper_chest',
    'chest_lower': 'lower_chest',
    'chest_girth': 'chest_circumference',
    'lower_width': 'khbna',
    'shoulder_front': 'front_shoulder',
    'shoulder_back': 'back_shoulder',
    'shoulder_drop': 'shoulder_drop',
    'flipped_collar': 'collar_flip',
    'standard_collar': 'plain_neck',
    'teek': 'teek',
    'waist': 'waist',
    'hips': 'hips',
    # Historical/alternate spellings seen in older payloads.
    'takhalees': 'takhalis',
    'takhalus': 'takhalis',
    'khbna_legacy': 'khbna',
    'step_width_legacy': 'step_width',
}


def _build_canonical_lookup():
    lookup = {name: [name] for name in THOBE_FIELD_ORDER}
    for legacy_key, canonical_key in LEGACY_TO_CANONICAL.items():
        aliases = lookup.setdefault(canonical_key, [canonical_key])
        if legacy_key not in aliases:
            aliases.append(legacy_key)
    return lookup


CANONICAL_LOOKUP_KEYS = _build_canonical_lookup()


def resolve_measurement_value(measurements, canonical_key):
    """Return the first non-empty value for a canonical grid field key."""
    if not isinstance(measurements, dict) or not canonical_key:
        return None
    for key in CANONICAL_LOOKUP_KEYS.get(canonical_key, [canonical_key]):
        value = measurements.get(key)
        if value not in (None, '', 'null'):
            return value
    return None


def canonical_key_for_legacy(legacy_key):
    """Return thobe canonical key for a legacy payload key, or the key itself."""
    return LEGACY_TO_CANONICAL.get(legacy_key, legacy_key)
