"""Shared measurement grid layout for PDF studio and document rendering."""

from apps.documents.measurement_aliases import resolve_measurement_value
from apps.orders.measurement_utils import ordered_measurement_keys


def index_fields_by_grid(field_map):
    """Map (row, col) -> (field_name, meta) using pdf_grid_row/col on field_map entries."""
    by_pos = {}
    for name, meta in field_map.items():
        row = meta.get('pdf_grid_row')
        col = meta.get('pdf_grid_col')
        if not row or not col:
            continue
        pos = (int(row), int(col))
        if pos not in by_pos:
            by_pos[pos] = (name, meta)
    return by_pos


def _label_from_meta(name, meta, lang, label_fn):
    if label_fn is not None:
        return label_fn(name, meta, lang)
    fallback = str(name).replace('_', ' ').title()
    if lang == 'ur':
        return meta.get('label_ur') or meta.get('label_en') or fallback
    if lang == 'ar':
        return meta.get('label_ar') or meta.get('label_en') or fallback
    return meta.get('label_en') or fallback


def _measurement_value(measurements, field_name):
    """Read a value by field name; fall back to thobe aliases for old grids."""
    if not isinstance(measurements, dict):
        return None
    value = measurements.get(field_name)
    if value not in (None, '', 'null'):
        return value
    return resolve_measurement_value(measurements, field_name)


def build_measurement_grid_cells(
    measurements,
    field_map,
    lang,
    cols,
    rows,
    *,
    show_all_slots=True,
    label_fn=None,
):
    """
    Build grid cell payloads for HTML/PDF renderers.

    When ``show_all_slots`` is True and fields have grid coordinates, every
    slot in the cols x rows grid is emitted (labels always; empty values as None).
    Otherwise falls back to payload-order placement for legacy orders.
    """
    measurements = measurements if isinstance(measurements, dict) else {}
    by_pos = index_fields_by_grid(field_map)

    if show_all_slots and by_pos:
        cells = []
        for row in range(1, rows + 1):
            for col in range(1, cols + 1):
                entry = by_pos.get((row, col))
                if not entry:
                    cells.append({
                        'key': '',
                        'label': '',
                        'value': None,
                        'unit': '',
                        'row': row,
                        'col': col,
                        'sequence': None,
                        'has_value': False,
                    })
                    continue
                name, meta = entry
                value = _measurement_value(measurements, name)
                has_value = value not in (None, '', 'null')
                cells.append({
                    'key': name,
                    'label': _label_from_meta(name, meta, lang, label_fn),
                    'value': value if has_value else None,
                    'unit': measurements.get('unit') or meta.get('unit') or 'cm',
                    'row': row,
                    'col': col,
                    'sequence': meta.get('display_order'),
                    'has_value': has_value,
                })
        return cells

    cells = []
    used = set()
    sequence = 0
    for key in ordered_measurement_keys(measurements):
        value = measurements.get(key)
        if value in (None, '', 'null'):
            continue
        sequence += 1
        meta = field_map.get(key, {})
        row = meta.get('pdf_grid_row')
        col = meta.get('pdf_grid_col')
        if not row or not col:
            for candidate_row in range(1, rows + 1):
                for candidate_col in range(1, cols + 1):
                    if (candidate_row, candidate_col) not in used:
                        row, col = candidate_row, candidate_col
                        break
                if row and col and (row, col) not in used:
                    break
        row = int(row or 1)
        col = int(col or 1)
        used.add((row, col))
        cells.append({
            'key': key,
            'label': _label_from_meta(key, meta, lang, label_fn),
            'value': value,
            'unit': measurements.get('unit') or meta.get('unit') or 'cm',
            'row': row,
            'col': col,
            'sequence': meta.get('display_order') or sequence,
            'has_value': True,
        })
    return cells
