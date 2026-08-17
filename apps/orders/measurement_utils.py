"""Helpers for tailor/rider/customer measurement payloads."""

from decimal import Decimal

from rest_framework.exceptions import ValidationError

METADATA_KEYS = frozenset({'unit', 'title', 'recorded_unit', 'notes', '_order'})
MEASUREMENT_ORDER_KEY = '_order'
MAX_MEASUREMENT_NOTES_LENGTH = 2000
SUPPORTED_UNITS = frozenset({'cm', 'inches'})


def is_measurement_field(key):
    return key not in METADATA_KEYS


def normalize_unit(unit):
    """Normalize client unit strings to cm or inches."""
    if unit in (None, ''):
        return 'cm'

    normalized = str(unit).strip().lower()
    if normalized in {'in', 'inch', 'inches', '"'}:
        return 'inches'
    if normalized in {'cm', 'centimeter', 'centimeters'}:
        return 'cm'

    raise ValidationError({
        'unit': f"Unsupported measurement unit '{unit}'. Use 'cm' or 'inches'."
    })


def _coerce_measurement_value(value):
    if value is None or value == '':
        return value
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float, Decimal)):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return value
        try:
            if '.' in stripped:
                return float(stripped)
            return int(stripped)
        except ValueError:
            return stripped
    return value


def measurement_field_keys(measurements):
    """Return body-measurement keys in the current dict iteration order."""
    if not isinstance(measurements, dict):
        return []
    return [key for key in measurements.keys() if is_measurement_field(key)]


def with_measurement_order(measurements):
    """
    Persist payload key order in ``_order``.

    PostgreSQL jsonb does not keep JSON object key order, so the PDF (and any
    later read) would otherwise reshuffle fields. Existing ``_order`` is kept
    and any new keys are appended.
    """
    if not isinstance(measurements, dict):
        return measurements

    field_keys = measurement_field_keys(measurements)
    if not field_keys:
        return measurements

    stored = dict(measurements)
    existing = stored.get(MEASUREMENT_ORDER_KEY)
    if isinstance(existing, list) and existing:
        ordered = [key for key in existing if key in field_keys]
        for key in field_keys:
            if key not in ordered:
                ordered.append(key)
        stored[MEASUREMENT_ORDER_KEY] = ordered
    else:
        stored[MEASUREMENT_ORDER_KEY] = field_keys
    return stored


def public_measurements(measurements):
    """Return a client-facing copy without the internal ``_order`` key."""
    if not isinstance(measurements, dict):
        return measurements
    return {
        key: value
        for key, value in measurements.items()
        if key != MEASUREMENT_ORDER_KEY
    }


def ordered_measurement_keys(measurements):
    """Keys to render, preferring stored ``_order`` when present."""
    if not isinstance(measurements, dict):
        return []
    field_keys = measurement_field_keys(measurements)
    explicit = measurements.get(MEASUREMENT_ORDER_KEY)
    if not isinstance(explicit, list) or not explicit:
        return field_keys
    ordered = [key for key in explicit if key in field_keys]
    for key in field_keys:
        if key not in ordered:
            ordered.append(key)
    return ordered


def measurement_field_values(measurements):
    """Return only body measurement keys/values from a stored payload."""
    if not isinstance(measurements, dict):
        return {}
    return {
        key: value
        for key, value in measurements.items()
        if is_measurement_field(key)
    }


def has_measurement_values(measurements):
    """True when at least one measurement field has a non-empty value."""
    for value in measurement_field_values(measurements).values():
        if value not in (None, '', 'null'):
            return True
    return False


def get_measurement_unit(measurements, default='cm'):
    if not isinstance(measurements, dict):
        return default
    try:
        return normalize_unit(measurements.get('unit', default))
    except ValidationError:
        return default


def _normalize_notes(notes):
    if notes in (None, ''):
        return None
    text = str(notes).strip()
    if not text:
        return None
    if len(text) > MAX_MEASUREMENT_NOTES_LENGTH:
        raise ValidationError({
            'notes': f'Notes must be at most {MAX_MEASUREMENT_NOTES_LENGTH} characters.',
        })
    return text


def prepare_measurements_payload(raw_measurements, *, unit=None, title=None, notes=None):
    """
    Build a stored measurements JSON object with metadata.

    Values are stored as entered; ``unit`` records how they were captured.
    """
    if not isinstance(raw_measurements, dict):
        raise ValidationError({'measurements': 'Measurements must be a dictionary/JSON object.'})

    field_values = {
        key: value
        for key, value in raw_measurements.items()
        if is_measurement_field(key)
    }
    if not field_values:
        raise ValidationError({'measurements': 'Measurements cannot be empty.'})

    resolved_unit = normalize_unit(unit if unit is not None else raw_measurements.get('unit'))
    stored = {
        key: _coerce_measurement_value(value)
        for key, value in field_values.items()
    }
    stored['unit'] = resolved_unit

    resolved_title = title if title is not None else raw_measurements.get('title')
    if resolved_title:
        stored['title'] = resolved_title

    resolved_notes = notes if notes is not None else raw_measurements.get('notes')
    normalized_notes = _normalize_notes(resolved_notes)
    if normalized_notes:
        stored['notes'] = normalized_notes

    return with_measurement_order(stored)
