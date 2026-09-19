from django.http import FileResponse, Http404
from django.template.response import TemplateResponse

from apps.core.product_overview import get_client_pdf_path, load_product_overview


def product_overview_view(request):
    """Public client product overview — chapter-based markdown rendered as HTML."""
    document = load_product_overview()
    if not document.chapters:
        raise Http404('Product overview chapters not found.')

    return TemplateResponse(
        request,
        'core/product_overview.html',
        {
            'document': document,
            'page_title': document.title,
            'meta_description': document.description,
        },
    )


def product_overview_pdf_view(request):
    """Serve the pre-built client overview PDF."""
    pdf_path = get_client_pdf_path()
    if not pdf_path.is_file():
        raise Http404(
            'PDF not available yet. Run: node scripts/export-client-overview-pdf.mjs'
        )

    return FileResponse(
        pdf_path.open('rb'),
        content_type='application/pdf',
        as_attachment=False,
        filename='Mgask-Product-Overview.pdf',
    )
