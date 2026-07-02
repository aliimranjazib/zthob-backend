"""Helpers for tailor/rider/customer measurement payloads."""

from decimal import Decimal

from rest_framework.exceptions import ValidationError

METADATA_KEYS = frozenset({'unit', 'title', 'recorded_unit'})
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


def prepare_measurements_payload(raw_measurements, *, unit=None, title=None):
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

    return stored
