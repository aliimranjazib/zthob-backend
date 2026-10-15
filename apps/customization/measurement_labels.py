"""Resolve shop/global measurement labels (EN/AR/UR) for API and PDF."""

from __future__ import annotations

from apps.customization.models import MeasurementField, ShopMeasurementField

LABEL_ATTR = {
    'en': 'display_name',
    'ar': 'display_name_ar',
    'ur': 'display_name_ur',
}


def pick_stored_label(
    global_field: MeasurementField | None,
    shop_row: ShopMeasurementField | None,
    attr: str,
    fallback: str,
) -> str:
    if shop_row is not None:
        value = getattr(shop_row, attr, '') or ''
        if value.strip():
            return value
    if global_field is not None:
        return getattr(global_field, attr, '') or fallback
    return fallback


def trilingual_labels(
    *,
    global_field: MeasurementField | None,
    shop_row: ShopMeasurementField | None,
    storage_name: str = '',
) -> tuple[str, str, str]:
    fallback_title = storage_name.replace('_', ' ').title() if storage_name else ''
    global_en = global_field.display_name if global_field else ''
    en = pick_stored_label(global_field, shop_row, 'display_name', global_en or fallback_title)
    ar = pick_stored_label(
        global_field,
        shop_row,
        'display_name_ar',
        (global_field.display_name_ar if global_field else '') or en,
    )
    ur = pick_stored_label(
        global_field,
        shop_row,
        'display_name_ur',
        (global_field.display_name_ur if global_field else '') or en,
    )
    return en, ar, ur


def localized_display_name(
    *,
    global_field: MeasurementField | None,
    shop_row: ShopMeasurementField | None,
    language: str,
    storage_name: str = '',
) -> str:
    en, ar, ur = trilingual_labels(
        global_field=global_field,
        shop_row=shop_row,
        storage_name=storage_name or (shop_row.name if shop_row else global_field.name if global_field else ''),
    )
    if language == 'ur' and ur.strip():
        return ur
    if language == 'ar' and ar.strip():
        return ar
    return en or storage_name.replace('_', ' ').title()


def merge_label_columns_from_write(
    *,
    row: dict,
    language: str,
    existing: ShopMeasurementField | None,
) -> dict[str, str]:
    """Map a single API ``display_name`` to the correct stored column for ``language``."""
    en = (existing.display_name if existing else '') or ''
    ar = (existing.display_name_ar if existing else '') or ''
    ur = (existing.display_name_ur if existing else '') or ''

    incoming = (row.get('display_name') or '').strip()
    if incoming:
        attr = LABEL_ATTR.get(language, 'display_name')
        if attr == 'display_name_ar':
            ar = incoming[:100]
        elif attr == 'display_name_ur':
            ur = incoming[:100]
        else:
            en = incoming[:100]

    return {
        'display_name': en[:100],
        'display_name_ar': ar[:100],
        'display_name_ur': ur[:100],
    }
