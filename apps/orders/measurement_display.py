"""Localized measurement rows for order detail APIs (shared with PDF label sources)."""

from __future__ import annotations

from apps.orders.measurement_utils import (
    FIELD_LABELS_KEY,
    get_measurement_unit,
    measurement_field_keys,
    ordered_measurement_keys,
    with_measurement_order,
)


def field_map_for_order(order) -> dict:
    """Platform or shop-custom field metadata keyed by storage name."""
    shop_id = getattr(order, 'shop_id', None)
    if shop_id:
        from apps.customization.services.shop_measurement_template import (
            build_pdf_field_map_for_shop,
        )

        shop_map = build_pdf_field_map_for_shop(shop_id)
        if shop_map:
            return shop_map

    from apps.documents.measurement_config import build_pdf_field_map

    return build_pdf_field_map()


def _label_from_meta(key: str, meta: dict, language: str) -> str:
    fallback = str(key).replace('_', ' ').title()
    if language == 'ur':
        return meta.get('label_ur') or meta.get('label_en') or fallback
    if language == 'ar':
        return meta.get('label_ar') or meta.get('label_en') or fallback
    return meta.get('label_en') or fallback


def _label_from_snapshot(key: str, snapshot: dict, language: str, meta: dict) -> str:
    entry = snapshot.get(key)
    if not isinstance(entry, dict):
        if entry not in (None, ''):
            return str(entry)
        return _label_from_meta(key, meta, language)
    if language == 'ur' and (entry.get('ur') or '').strip():
        return entry['ur']
    if language == 'ar' and (entry.get('ar') or '').strip():
        return entry['ar']
    if (entry.get('en') or '').strip():
        return entry['en']
    return _label_from_meta(key, meta, language)


def build_measurement_rows(
    measurements,
    *,
    field_map: dict,
    language: str = 'en',
    field_labels_snapshot: dict | None = None,
) -> list[dict]:
    """
    Ordered, localized label/value rows for UI.

    Uses ``_field_labels`` snapshot on the stored payload when present (historical
    accuracy); otherwise resolves from the current shop/platform field map.
    """
    if not measurements or not isinstance(measurements, dict):
        return []

    unit = get_measurement_unit(measurements)
    snapshot = field_labels_snapshot
    if snapshot is None and isinstance(measurements.get(FIELD_LABELS_KEY), dict):
        snapshot = measurements[FIELD_LABELS_KEY]

    rows = []
    for order_idx, key in enumerate(ordered_measurement_keys(measurements)):
        value = measurements.get(key)
        if value in (None, '', 'null'):
            continue
        meta = field_map.get(key, {})
        if snapshot:
            label = _label_from_snapshot(key, snapshot, language, meta)
        else:
            label = _label_from_meta(key, meta, language)
        rows.append(
            {
                'key': key,
                'label': label,
                'value': value,
                'unit': meta.get('unit') or unit,
                'display_order': meta.get('display_order') or (order_idx + 1),
            }
        )
    return rows


def attach_field_label_snapshot(measurements: dict, order) -> dict:
    """Persist EN/AR/UR labels at capture time under ``_field_labels``."""
    if not isinstance(measurements, dict):
        return measurements

    keys = measurement_field_keys(measurements)
    if not keys:
        return measurements

    field_map = field_map_for_order(order)
    snapshot = {}
    for key in keys:
        meta = field_map.get(key, {})
        snapshot[key] = {
            'en': meta.get('label_en') or str(key).replace('_', ' ').title(),
            'ar': meta.get('label_ar') or meta.get('label_en') or str(key),
            'ur': meta.get('label_ur') or meta.get('label_en') or str(key),
        }

    stored = dict(measurements)
    stored[FIELD_LABELS_KEY] = snapshot
    return with_measurement_order(stored)
