"""Canonical order-document sections and default layout.

Layout lives in the database so ops can reorder/hide sections without a deploy.
This catalog is the fallback when no template has been seeded yet.
"""

HEADER = 'header'
CUSTOMER = 'customer'
RIDERS = 'riders'
PERSON_ITEMS = 'person_items'
ORDER_SUMMARY = 'order_summary'
NOTES = 'notes'
STATUS_HISTORY = 'status_history'
COMMENTS_FOOTER = 'comments_footer'

SECTION_KEYS = (
    HEADER,
    CUSTOMER,
    RIDERS,
    PERSON_ITEMS,
    ORDER_SUMMARY,
    NOTES,
    STATUS_HISTORY,
    COMMENTS_FOOTER,
)

SECTION_CHOICES = [
    (HEADER, 'Header'),
    (CUSTOMER, 'Customer information'),
    (RIDERS, 'Riders'),
    (PERSON_ITEMS, 'Items by person (fabric, styles, measurements)'),
    (ORDER_SUMMARY, 'Order summary'),
    (NOTES, 'Notes & instructions'),
    (STATUS_HISTORY, 'Status history'),
    (COMMENTS_FOOTER, 'Comments & footer'),
]

DEFAULT_SECTION_SETTINGS = {
    HEADER: {},
    CUSTOMER: {},
    RIDERS: {'hide_if_empty': True},
    PERSON_ITEMS: {
        'show_fabric': True,
        'show_styles': True,
        'show_measurements': True,
        'show_instructions': True,
        'measurement_cols': 5,
        'measurement_rows': 4,
        # Keep the client's paper grid (col 1 on the left) even in Arabic PDFs.
        'measurement_grid_ltr': True,
        'show_sequence_numbers': True,
    },
    ORDER_SUMMARY: {},
    NOTES: {'hide_if_empty': True},
    STATUS_HISTORY: {'hide_if_empty': True, 'max_rows': 4},
    COMMENTS_FOOTER: {},
}

DEFAULT_TEMPLATE_SLUG = 'order_receipt'
DEFAULT_TEMPLATE_NAME = 'Order Receipt'


def default_sections():
    """Return ordered default section definitions."""
    return [
        {
            'key': key,
            'display_order': index,
            'is_visible': True,
            'settings': dict(DEFAULT_SECTION_SETTINGS.get(key, {})),
        }
        for index, key in enumerate(SECTION_KEYS, start=1)
    ]
