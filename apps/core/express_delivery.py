"""Helpers for admin-configurable express delivery durations."""

from copy import deepcopy

EXPRESS_UNIT_HOURS = 'hours'
EXPRESS_UNIT_DAYS = 'days'
VALID_EXPRESS_UNITS = frozenset({EXPRESS_UNIT_HOURS, EXPRESS_UNIT_DAYS})


def default_express_delivery_options(max_days=10):
    """
    Default catalog for tailor express options.

    Includes a 6-hour option plus 1..max_days day options.
    """
    try:
        max_days = int(max_days or 10)
    except (TypeError, ValueError):
        max_days = 10
    max_days = max(max_days, 1)

    options = [
        {
            'value': 6,
            'unit': EXPRESS_UNIT_HOURS,
            'label': '6 Hours',
        }
    ]
    for day in range(1, max_days + 1):
        options.append({
            'value': day,
            'unit': EXPRESS_UNIT_DAYS,
            'label': f'{day} Day' if day == 1 else f'{day} Days',
        })
    return options


def normalize_express_option(raw):
    """
    Normalize one option dict.

    Accepts:
      { "value": 6, "unit": "hours", "label": "6 Hours" }
      { "hours": 6, "display_name": "6 Hours" }
      { "days": 2, "display_name": "2 Days" }
    """
    if not isinstance(raw, dict):
        return None

    unit = (raw.get('unit') or '').strip().lower() or None
    value = raw.get('value')

    if value is None and raw.get('hours') is not None:
        unit = EXPRESS_UNIT_HOURS
        value = raw.get('hours')
    elif value is None and raw.get('days') is not None:
        unit = EXPRESS_UNIT_DAYS
        value = raw.get('days')

    if unit not in VALID_EXPRESS_UNITS:
        return None
    try:
        value = int(value)
    except (TypeError, ValueError):
        return None
    if value <= 0:
        return None

    label = (
        raw.get('label')
        or raw.get('display_name')
        or (
            f'{value} Hour' if value == 1 and unit == EXPRESS_UNIT_HOURS
            else f'{value} Hours' if unit == EXPRESS_UNIT_HOURS
            else f'{value} Day' if value == 1
            else f'{value} Days'
        )
    )

    return {
        'value': value,
        'unit': unit,
        'label': label,
        'hours': value if unit == EXPRESS_UNIT_HOURS else None,
        'days': value if unit == EXPRESS_UNIT_DAYS else None,
    }


def get_express_delivery_options(system_settings=None, *, language='en', translate=None):
    """
    Return public express options for the tailor config API.

    Uses SystemSettings.express_delivery_options when set; otherwise builds
    defaults from express_delivery_max_days (includes 6 Hours).
    """
    if system_settings is None:
        from apps.core.models import SystemSettings
        system_settings = SystemSettings.get_active_settings()

    raw_options = getattr(system_settings, 'express_delivery_options', None)
    if not raw_options:
        raw_options = default_express_delivery_options(
            getattr(system_settings, 'express_delivery_max_days', 10)
        )

    translate_fn = translate or (lambda text, _lang: text)
    options = []
    seen = set()
    for raw in raw_options:
        normalized = normalize_express_option(raw)
        if not normalized:
            continue
        key = (normalized['unit'], normalized['value'])
        if key in seen:
            continue
        seen.add(key)
        display = translate_fn(normalized['label'], language)
        options.append({
            'value': normalized['value'],
            'unit': normalized['unit'],
            'hours': normalized['hours'],
            'days': normalized['days'],
            'display_name': display,
            # Backward-compatible alias used by older tailor apps
            'label': display,
        })
    return options


def is_allowed_express_selection(value, unit, system_settings=None):
    """True when (value, unit) exists in the admin-configured option list."""
    unit = (unit or EXPRESS_UNIT_DAYS).strip().lower()
    try:
        value = int(value)
    except (TypeError, ValueError):
        return False

    for option in get_express_delivery_options(system_settings, language='en'):
        if option['unit'] == unit and option['value'] == value:
            return True
    return False


def clone_default_express_options(max_days=10):
    return deepcopy(default_express_delivery_options(max_days))
