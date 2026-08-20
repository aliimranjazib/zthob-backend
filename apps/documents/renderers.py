"""PDF engines for the order document.

HTML (WeasyPrint) is the layout source of truth. ReportLab is a production
fallback so downloads never fail if WeasyPrint/system libs are missing.
"""
import logging
from functools import lru_cache

from django.template.loader import render_to_string

from apps.documents.catalog import (
    COMMENTS_FOOTER,
    CUSTOMER,
    HEADER,
    NOTES,
    ORDER_SUMMARY,
    PERSON_ITEMS,
    RIDERS,
    STATUS_HISTORY,
)

logger = logging.getLogger(__name__)

SECTION_PARTIALS = {
    HEADER: 'documents/order/partials/header.html',
    CUSTOMER: 'documents/order/partials/customer.html',
    RIDERS: 'documents/order/partials/riders.html',
    PERSON_ITEMS: 'documents/order/partials/person_items.html',
    ORDER_SUMMARY: 'documents/order/partials/order_summary.html',
    NOTES: 'documents/order/partials/notes.html',
    STATUS_HISTORY: 'documents/order/partials/status_history.html',
    COMMENTS_FOOTER: 'documents/order/partials/comments_footer.html',
}


def render_order_html(context, layout):
    section_html = []
    for section in layout.sections:
        template_name = SECTION_PARTIALS.get(section.key)
        if not template_name:
            continue
        if section.settings.get('hide_if_empty') and _section_is_empty(section.key, context):
            continue
        section_html.append(render_to_string(template_name, {
            **context,
            'section': section,
        }))
    return render_to_string('documents/order/document.html', {
        **context,
        'section_html': section_html,
    })


def _section_is_empty(key, context):
    if key == RIDERS:
        riders = context.get('riders') or {}
        return not riders.get('measurement') and not riders.get('delivery')
    if key == NOTES:
        order = context.get('order') or {}
        return not order.get('special_instructions') and not order.get('notes')
    if key == STATUS_HISTORY:
        return not context.get('status_history')
    if key == PERSON_ITEMS:
        return not context.get('items') and not context.get('rider_measurements')
    return False


@lru_cache(maxsize=1)
def html_engine_available():
    try:
        import weasyprint  # noqa: F401
        return True
    except Exception:
        return False


def render_html_pdf(html):
    from weasyprint import HTML

    return HTML(string=html, base_url='.').write_pdf()


def render_reportlab_pdf(order, lang):
    from apps.tailors.services.order_pdf import generate_order_pdf_reportlab

    return generate_order_pdf_reportlab(order, lang=lang)
