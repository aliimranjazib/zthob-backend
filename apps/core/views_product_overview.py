from django.http import Http404
from django.template.response import TemplateResponse

from apps.core.product_overview import load_product_overview


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
