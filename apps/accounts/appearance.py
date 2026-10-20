"""User appearance / theme preferences (owner app sync across devices)."""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from django.utils import timezone

APPEARANCE_VERSION = 1

THEME_MODE_LIGHT = 'light'
THEME_MODE_DARK = 'dark'
THEME_MODE_SYSTEM = 'system'
THEME_MODES = frozenset({THEME_MODE_LIGHT, THEME_MODE_DARK, THEME_MODE_SYSTEM})

# Presets shared with Flutter owner app (validate writes against this set).
THEME_PRESETS: dict[str, str] = {
    'mgask_default': '#990404',
}

HEX_COLOR_RE = re.compile(r'^#[0-9A-Fa-f]{6}$')

DEFAULT_APPEARANCE: dict[str, Any] = {
    'version': APPEARANCE_VERSION,
    'mode': THEME_MODE_SYSTEM,
    'preset_id': 'mgask_default',
    'seed_color': THEME_PRESETS['mgask_default'],
}


def _normalize_hex(value: str) -> str:
    cleaned = value.strip()
    if not HEX_COLOR_RE.match(cleaned):
        raise ValueError('seed_color must be a hex color in #RRGGBB format.')
    return cleaned.upper()


def normalize_appearance(raw: dict[str, Any] | None) -> dict[str, Any]:
    """
    Validate and merge appearance payload. Returns a full document for API responses.
    """
    if raw is None:
        return deepcopy(DEFAULT_APPEARANCE)
    if not isinstance(raw, dict):
        raise ValueError('appearance must be an object.')
    if not raw:
        return deepcopy(DEFAULT_APPEARANCE)

    version = raw.get('version', APPEARANCE_VERSION)
    if version != APPEARANCE_VERSION:
        raise ValueError(f'Unsupported appearance version: {version}')

    mode = raw.get('mode', DEFAULT_APPEARANCE['mode'])
    if mode not in THEME_MODES:
        raise ValueError(
            f'mode must be one of: {", ".join(sorted(THEME_MODES))}.'
        )

    preset_id = raw.get('preset_id', DEFAULT_APPEARANCE['preset_id'])
    if 'preset_id' in raw and preset_id in (None, ''):
        preset_id = None

    if preset_id:
        if preset_id not in THEME_PRESETS:
            allowed = ', '.join(sorted(THEME_PRESETS))
            raise ValueError(f'preset_id must be one of: {allowed}.')
        seed_color = THEME_PRESETS[preset_id]
    else:
        seed = raw.get('seed_color')
        if seed in (None, ''):
            raise ValueError('seed_color is required when preset_id is not set.')
        seed_color = _normalize_hex(str(seed))

    return {
        'version': APPEARANCE_VERSION,
        'mode': mode,
        'preset_id': preset_id,
        'seed_color': seed_color,
    }


def appearance_for_user(user) -> dict[str, Any]:
    """Resolved appearance for API responses."""
    stored = getattr(user, 'appearance', None) or {}
    if not stored:
        return deepcopy(DEFAULT_APPEARANCE)
    try:
        return normalize_appearance(stored)
    except ValueError:
        return deepcopy(DEFAULT_APPEARANCE)


def apply_appearance_update(user, raw: dict[str, Any]) -> None:
    """Persist validated appearance on user."""
    _assert_can_update_app_theme(user)
    normalized = normalize_appearance(raw)
    user.appearance = normalized
    user.appearance_updated_at = timezone.now()


def _assert_can_update_app_theme(user) -> None:
    """Theme save is promised on Tailor Plus and Owner Plus only."""
    from apps.tailors.models import TailorProfile
    from apps.tailors.services.plans.owner_limits import OwnerPlanLimitError
    from apps.tailors.services.plans.owner_plus import is_owner_plus_active
    from apps.tailors.services.shop_plus import TailorPlusLimitError, is_shop_plus_active

    if is_owner_plus_active(owner=user):
        return
    shop = getattr(user, 'tailor_profile', None)
    if is_shop_plus_active(shop):
        return
    owns_shop = (
        TailorProfile.objects.filter(owner=user)
        .exclude(shop_name__isnull=True)
        .exclude(shop_name='')
        .exists()
    )
    if owns_shop:
        raise OwnerPlanLimitError(
            'Owner Plus is required to customize store branding.',
            entitlement='app_theme',
        )
    raise TailorPlusLimitError(
        'Tailor Plus is required to customize store branding.',
        entitlement='app_theme',
    )
