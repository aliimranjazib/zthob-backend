"""Public API for complete order documents."""
import logging

from django.conf import settings

from apps.documents.context import build_order_document_context
from apps.documents.layout import resolve_layout
from apps.documents.renderers import (
    html_engine_available,
    render_html_pdf,
    render_order_html,
    render_reportlab_pdf,
)

logger = logging.getLogger(__name__)


def _requested_engine(layout, engine=None):
    requested = (engine or getattr(settings, 'ORDER_PDF_ENGINE', None) or layout.engine or 'auto')
    requested = str(requested).strip().lower()
    if requested not in ('auto', 'html', 'reportlab'):
        return 'auto'
    return requested


def generate_order_html(order, lang='en', template=None, layout=None, measurement_field_map=None):
    layout = layout or resolve_layout(template)
    context = build_order_document_context(
        order, lang, layout, measurement_field_map=measurement_field_map,
    )
    return render_order_html(context, layout), context, layout


def generate_order_document(order, lang='en', *, engine=None, template=None):
    """
    Render the complete order PDF.

    engine: auto | html | reportlab
    HTML is preferred. ReportLab is used when HTML is unavailable or fails.
    """
    layout = resolve_layout(template)
    requested = _requested_engine(layout, engine)

    if requested == 'reportlab':
        return render_reportlab_pdf(order, lang)

    if requested in ('auto', 'html'):
        if html_engine_available():
            try:
                html, _context, _layout = generate_order_html(order, lang=lang, layout=layout)
                pdf_bytes = render_html_pdf(html)
                if pdf_bytes and pdf_bytes.startswith(b'%PDF'):
                    return pdf_bytes
            except Exception:
                logger.exception(
                    'HTML PDF engine failed for order %s; falling back to ReportLab',
                    getattr(order, 'id', None),
                )
                if requested == 'html':
                    raise
        elif requested == 'html':
            raise RuntimeError('WeasyPrint is not installed; cannot render HTML PDFs.')

    return render_reportlab_pdf(order, lang)
