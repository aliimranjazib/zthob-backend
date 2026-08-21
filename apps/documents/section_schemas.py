"""Schema-driven section settings for PDF Layout Studio and template defaults."""

from apps.documents.catalog import (
    COMMENTS_FOOTER,
    CUSTOMER,
    DEFAULT_SECTION_SETTINGS,
    HEADER,
    NOTES,
    ORDER_SUMMARY,
    PERSON_ITEMS,
    RIDERS,
    SECTION_KEYS,
    STATUS_HISTORY,
)


def merge_section_settings(section_key, settings=None):
    """Merge stored settings with catalog defaults for a section key."""
    merged = dict(DEFAULT_SECTION_SETTINGS.get(section_key, {}))
    if isinstance(settings, dict):
        merged.update(settings)
    return merged


def _field(key, field_type, label, *, group='General', default=None, hint='', min_value=None, max_value=None):
    item = {
        'key': key,
        'type': field_type,
        'label': label,
        'group': group,
    }
    if default is not None:
        item['default'] = default
    if hint:
        item['hint'] = hint
    if min_value is not None:
        item['min'] = min_value
    if max_value is not None:
        item['max'] = max_value
    return item


SECTION_SETTING_SCHEMAS = {
    HEADER: [
        _field('show_status_strip', 'bool', 'Show status strip', group='Display', default=True),
        _field('show_order_number', 'bool', 'Show order number in banner', group='Display', default=True),
        _field(
            'brand_text', 'text', 'Brand name',
            group='Content', default='MGASK',
            hint='Shown in the red header banner.',
        ),
    ],
    CUSTOMER: [
        _field('show_service_mode', 'bool', 'Show service mode', group='Fields', default=True),
        _field('show_measured_by', 'bool', 'Show measured by', group='Fields', default=True),
        _field('show_address', 'bool', 'Show delivery address', group='Fields', default=True),
    ],
    RIDERS: [
        _field(
            'hide_if_empty', 'bool', 'Hide when no riders',
            group='Behavior', default=True,
            hint='Section is omitted from PDF when empty.',
        ),
        _field('show_measurement_rider', 'bool', 'Show measurement rider', group='Fields', default=True),
        _field('show_delivery_rider', 'bool', 'Show delivery rider', group='Fields', default=True),
        _field('show_phone', 'bool', 'Show rider phone numbers', group='Fields', default=True),
    ],
    PERSON_ITEMS: [
        _field('show_fabric', 'bool', 'Show fabric details', group='Fields', default=True),
        _field('show_fabric_photos', 'bool', 'Show fabric photos', group='Fields', default=True),
        _field('show_sku', 'bool', 'Show SKU', group='Fields', default=True),
        _field('show_item_ready', 'bool', 'Show ready status', group='Fields', default=True),
        _field('show_styles', 'bool', 'Show custom styles', group='Fields', default=True),
        _field('show_measurements', 'bool', 'Show measurement grid', group='Fields', default=True),
        _field('show_instructions', 'bool', 'Show instructions', group='Fields', default=True),
        _field('show_sequence_numbers', 'bool', 'Show sequence numbers', group='Fields', default=True),
        _field(
            'show_all_measurement_slots', 'bool', 'Show all grid slots (including empty)',
            group='Layout', default=True,
            hint='Always render the full measurement grid with labels; empty values show as —.',
        ),
        _field(
            'measurement_grid_ltr', 'bool', 'Keep grid columns left-to-right',
            group='Layout', default=True,
            hint='When on, column 1 stays on the left (client sheet layout). Arabic/Urdu labels still render RTL inside each cell.',
        ),
    ],
    ORDER_SUMMARY: [
        _field('show_tailor_block', 'bool', 'Show tailor / shop block', group='Fields', default=True),
        _field('show_estimated_delivery', 'bool', 'Show estimated delivery', group='Fields', default=True),
        _field('show_actual_delivery', 'bool', 'Show actual delivery', group='Fields', default=True),
        _field('show_appointment', 'bool', 'Show appointment', group='Fields', default=True),
        _field('show_stitching_done', 'bool', 'Show stitching completion date', group='Fields', default=True),
    ],
    NOTES: [
        _field(
            'hide_if_empty', 'bool', 'Hide when empty',
            group='Behavior', default=True,
        ),
        _field('show_special_instructions', 'bool', 'Show special instructions', group='Fields', default=True),
        _field('show_internal_notes', 'bool', 'Show internal notes', group='Fields', default=True),
    ],
    STATUS_HISTORY: [
        _field(
            'hide_if_empty', 'bool', 'Hide when empty',
            group='Behavior', default=True,
        ),
        _field('max_rows', 'number', 'Maximum rows', group='Layout', default=4, min_value=1, max_value=20),
        _field('show_changed_by', 'bool', 'Show changed-by column', group='Fields', default=True),
        _field('show_notes_column', 'bool', 'Show notes column', group='Fields', default=True),
    ],
    COMMENTS_FOOTER: [
        _field('show_comments_box', 'bool', 'Show handwriting comments box', group='Display', default=True),
        _field('show_generated_footer', 'bool', 'Show generated footer line', group='Display', default=True),
        _field(
            'footer_text', 'text', 'Custom footer text',
            group='Content', default='',
            hint='Optional. Leave empty to use the default platform line.',
        ),
    ],
}


def schema_for_section(section_key):
    return SECTION_SETTING_SCHEMAS.get(section_key, [])


def section_schemas_for_studio():
    """Return all section schemas keyed by section key for the layout studio."""
    return {
        key: schema_for_section(key)
        for key in SECTION_KEYS
    }
