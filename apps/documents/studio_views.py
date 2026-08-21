"""PDF Layout Studio — staff UI for section order and measurement grid."""
import json

from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_http_methods

from apps.customization.models import MeasurementField
from apps.documents.measurement_fields import serialize_measurement_fields_for_studio
from apps.documents.catalog import PERSON_ITEMS, SECTION_CHOICES
from apps.documents.layout import resolve_layout, resolve_layout_from_draft
from apps.documents.models import PdfDocumentSection, PdfDocumentTemplate
from apps.documents.section_schemas import merge_section_settings, section_schemas_for_studio
from apps.documents.service import generate_order_html
from apps.orders.models import Order


def _section_labels():
    return dict(SECTION_CHOICES)


def _default_template():
    template = (
        PdfDocumentTemplate.objects.filter(is_active=True, is_default=True)
        .prefetch_related('sections')
        .first()
    )
    if template is None:
        template = (
            PdfDocumentTemplate.objects.filter(is_active=True)
            .prefetch_related('sections')
            .order_by('-version', 'id')
            .first()
        )
    return template


def _person_items_settings(template):
    section = template.sections.filter(key=PERSON_ITEMS).first()
    if not section:
        return {}
    return section.settings or {}


def _grid_dimensions(settings):
    return {
        'cols': int(settings.get('measurement_cols') or 5),
        'rows': int(settings.get('measurement_rows') or 4),
    }


def _serialize_template(template):
    return {
        'id': template.id,
        'name': template.name,
        'slug': template.slug,
        'version': template.version,
        'engine': template.engine,
        'is_default': template.is_default,
    }


def _serialize_sections(template):
    labels = _section_labels()
    sections = template.sections.order_by('display_order', 'id')
    return [
        {
            'id': section.id,
            'key': section.key,
            'label': labels.get(section.key, section.key),
            'display_order': section.display_order,
            'is_visible': section.is_visible,
            'settings': merge_section_settings(section.key, section.settings or {}),
        }
        for section in sections
    ]


def _serialize_measurement_fields():
    return serialize_measurement_fields_for_studio()


def _sample_orders(limit=20):
    qs = Order.objects.select_related('customer').order_by('-id')[:limit]
    return [
        {'id': order.id, 'order_number': order.order_number}
        for order in qs
    ]


def _build_field_map_overrides(measurement_fields):
    """Merge studio draft measurement positions into the PDF field map."""
    if not measurement_fields:
        return None
    from apps.tailors.services.order_pdf import _measurement_field_map

    field_map = _measurement_field_map()
    for item in measurement_fields:
        name = item.get('name')
        if not name or name not in field_map:
            continue
        if item.get('display_order') is not None:
            field_map[name]['display_order'] = int(item['display_order'])
        if item.get('pdf_grid_row'):
            field_map[name]['pdf_grid_row'] = int(item['pdf_grid_row'])
        if item.get('pdf_grid_col'):
            field_map[name]['pdf_grid_col'] = int(item['pdf_grid_col'])
    return field_map


def _parse_json_body(request):
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


@staff_member_required
@require_GET
def layout_studio_page(request):
    template = _default_template()
    person_settings = merge_section_settings(PERSON_ITEMS, _person_items_settings(template) if template else {})
    grid = _grid_dimensions(person_settings)
    context = {
        'template': template,
        'grid_cols': grid['cols'],
        'grid_rows': grid['rows'],
        'sample_orders': _sample_orders(),
    }
    return render(request, 'documents/studio/layout.html', context)


@staff_member_required
@require_GET
def layout_studio_api_get(request):
    template = _default_template()
    if template is None:
        return JsonResponse({'error': 'No PDF template found. Run migrations first.'}, status=404)

    person_settings = _person_items_settings(template)
    return JsonResponse({
        'template': _serialize_template(template),
        'sections': _serialize_sections(template),
        'measurement_fields': _serialize_measurement_fields(),
        'grid': _grid_dimensions(person_settings),
        'sample_orders': _sample_orders(),
        'section_labels': _section_labels(),
        'section_schemas': section_schemas_for_studio(),
    })


@staff_member_required
@require_http_methods(['PUT', 'POST'])
def layout_studio_api_save(request):
    payload = _parse_json_body(request)
    if payload is None:
        return JsonResponse({'error': 'Invalid JSON body.'}, status=400)

    template = _default_template()
    if template is None:
        return JsonResponse({'error': 'No PDF template found.'}, status=404)

    sections_data = payload.get('sections')
    if not isinstance(sections_data, list):
        return JsonResponse({'error': 'sections must be a list.'}, status=400)

    with transaction.atomic():
        for index, item in enumerate(sections_data, start=1):
            section_id = item.get('id')
            if not section_id:
                continue
            section = get_object_or_404(
                PdfDocumentSection,
                id=section_id,
                template=template,
            )
            section.display_order = int(item.get('display_order', index))
            section.is_visible = bool(item.get('is_visible', True))
            if isinstance(item.get('settings'), dict):
                section.settings = item['settings']
            section.save(update_fields=['display_order', 'is_visible', 'settings', 'updated_at'])

    return JsonResponse({
        'success': True,
        'sections': _serialize_sections(template),
    })


@staff_member_required
@require_http_methods(['PUT', 'POST'])
def layout_studio_api_save_measurements(request):
    payload = _parse_json_body(request)
    if payload is None:
        return JsonResponse({'error': 'Invalid JSON body.'}, status=400)

    fields_data = payload.get('fields')
    if not isinstance(fields_data, list):
        return JsonResponse({'error': 'fields must be a list.'}, status=400)

    updated = 0
    with transaction.atomic():
        for index, item in enumerate(fields_data, start=1):
            field_id = item.get('id')
            if not field_id:
                continue
            field = get_object_or_404(MeasurementField, id=field_id, is_active=True)
            field.display_order = int(item.get('display_order', index))
            row = item.get('pdf_grid_row')
            col = item.get('pdf_grid_col')
            field.pdf_grid_row = int(row) if row else None
            field.pdf_grid_col = int(col) if col else None
            field.save(update_fields=[
                'display_order', 'pdf_grid_row', 'pdf_grid_col', 'updated_at',
            ])
            updated += 1

    return JsonResponse({
        'success': True,
        'updated': updated,
        'measurement_fields': _serialize_measurement_fields(),
    })


def _order_for_preview(order_id):
    return Order.objects.select_related(
        'customer',
        'tailor',
        'tailor__tailor_profile',
        'measurement_rider__rider_profile',
        'delivery_rider__rider_profile',
        'delivery_address',
    ).prefetch_related(
        'order_items__fabric',
        'order_items__family_member',
        'order_items__customer_fabric_images',
        'status_history__changed_by',
    ).get(id=order_id)


@staff_member_required
@require_http_methods(['GET', 'POST'])
def layout_studio_preview(request):
    if request.method == 'POST':
        payload = _parse_json_body(request) or {}
    else:
        payload = {
            'order_id': request.GET.get('order_id'),
            'lang': request.GET.get('lang', 'en'),
        }

    order_id = payload.get('order_id')
    if not order_id:
        return HttpResponse('Missing order_id', status=400, content_type='text/plain')

    lang = payload.get('lang') or 'en'
    if lang not in ('en', 'ar', 'ur'):
        lang = 'en'

    try:
        order = _order_for_preview(order_id)
    except Order.DoesNotExist:
        return HttpResponse('Order not found', status=404, content_type='text/plain')

    template = _default_template()
    draft_sections = payload.get('sections')
    draft_measurements = payload.get('measurement_fields')

    if isinstance(draft_sections, list) and template:
        layout = resolve_layout_from_draft(_serialize_template(template), draft_sections)
    else:
        layout = resolve_layout(template)

    field_map = _build_field_map_overrides(draft_measurements)
    html, _context, _layout = generate_order_html(
        order,
        lang=lang,
        layout=layout,
        measurement_field_map=field_map,
    )
    return HttpResponse(html, content_type='text/html; charset=utf-8')
