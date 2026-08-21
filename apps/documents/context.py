"""Build a JSON-serializable order document context.

This is the data layer. Templates and renderers must not query the order model
directly — they consume this dict so layout changes stay in HTML/admin.
"""
import base64
import mimetypes
from pathlib import Path

from django.conf import settings
from django.utils import timezone
from django.utils.html import escape

from apps.documents.catalog import PERSON_ITEMS
from apps.documents.section_schemas import merge_section_settings, STATUS_HISTORY
from apps.orders.measurement_utils import ordered_measurement_keys
from apps.tailors.services.order_pdf import (
    PDF_STATUS_HISTORY_MAX_ROWS,
    _choice_display,
    _custom_style_label_text,
    _customer_display_name,
    _customer_fabric_image_paths,
    _fmt_date,
    _fmt_datetime,
    _item_fabric_display_name,
    _localized_note,
    _measurement_field_map,
    _measurement_taken_by_name,
    _order_delivery_address,
    _person_header_detail_text,
    _resolve_media_file_path,
    _rider_contact_details,
    _style_image_path,
    _style_reference_image_paths,
    _translate_label,
    _truncate_style_comment,
)
from zthob.languages import is_rtl_language


def _label(text, lang):
    return _translate_label(text, lang)


def _file_to_data_uri(path):
    if not path:
        return None
    file_path = Path(path)
    if not file_path.is_file():
        return None
    mime = mimetypes.guess_type(str(file_path))[0] or 'image/png'
    try:
        encoded = base64.b64encode(file_path.read_bytes()).decode('ascii')
    except OSError:
        return None
    return f'data:{mime};base64,{encoded}'


def _arabic_font_uris():
    fonts_dir = Path(settings.BASE_DIR) / 'fonts'
    regular = fonts_dir / 'IBMPlexSansArabic-Regular.ttf'
    bold = fonts_dir / 'IBMPlexSansArabic-Bold.ttf'
    return {
        'regular': regular.as_uri() if regular.is_file() else '',
        'bold': bold.as_uri() if bold.is_file() else '',
    }


def _section_settings(layout, key):
    for section in layout.sections:
        if section.key == key:
            return section.settings
    return {}


def _measurement_label(key, meta, lang):
    fallback = str(key).replace('_', ' ').title()
    if lang == 'ur':
        return meta.get('label_ur') or meta.get('label_en') or fallback
    if lang == 'ar':
        return meta.get('label_ar') or meta.get('label_en') or fallback
    return meta.get('label_en') or fallback


def _build_measurement_cells(measurements, field_map, lang, cols, rows):
    if not measurements or not isinstance(measurements, dict):
        return []

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
            'label': _measurement_label(key, meta, lang),
            'value': value,
            'unit': measurements.get('unit') or meta.get('unit') or 'cm',
            'row': row,
            'col': col,
            'sequence': sequence,
        })
    return cells


def _style_cards(styles, lang):
    cards = []
    if not isinstance(styles, list):
        return cards
    for style in styles:
        if not isinstance(style, dict):
            continue
        comment = _truncate_style_comment((style.get('text') or '').strip())
        image = _file_to_data_uri(_style_image_path(style))
        refs = [
            uri for uri in (
                _file_to_data_uri(path) for path in _style_reference_image_paths(style)
            ) if uri
        ]
        label = _custom_style_label_text(style)
        if not label and not comment and not image and not refs:
            continue
        cards.append({
            'label': label,
            'comment': comment,
            'image': image,
            'references': refs,
        })
    return cards


def _recipient(item, order):
    if item.family_member_id and item.family_member:
        fm = item.family_member
        return {
            'name': fm.name or '—',
            'relationship': fm.relationship or '',
        }
    return {
        'name': _customer_display_name(getattr(order, 'customer', None)) or '—',
        'relationship': '',
    }


def _build_items(order, lang, layout, field_map):
    settings = _section_settings(layout, PERSON_ITEMS)
    cols = int(settings.get('measurement_cols') or 5)
    rows = int(settings.get('measurement_rows') or 4)
    items = []
    qs = order.order_items.select_related('fabric', 'family_member').prefetch_related(
        'customer_fabric_images',
    )
    for index, item in enumerate(qs.all(), start=1):
        measurements = item.measurements if isinstance(item.measurements, dict) else {}
        items.append({
            'index': index,
            'recipient': _recipient(item, order),
            'header': _person_header_detail_text(item, order),
            'fabric_name': _item_fabric_display_name(item, order, lang),
            'sku': item.fabric.sku if item.fabric and item.fabric.sku else '',
            'quantity': item.quantity,
            'is_ready': item.is_ready,
            'fabric_quantity': getattr(item, 'customer_fabric_quantity', None),
            'fabric_photos': [
                uri for uri in (
                    _file_to_data_uri(path) for path in _customer_fabric_image_paths(item)
                ) if uri
            ],
            'measurement_title': measurements.get('title') or '',
            'measurement_notes': measurements.get('notes') or '',
            'measurement_cells': _build_measurement_cells(measurements, field_map, lang, cols, rows),
            'styles': _style_cards(item.custom_styles, lang),
            'instructions': item.custom_instructions or '',
        })
    return items, cols, rows


def _rider_payload(rider):
    name, phone = _rider_contact_details(rider)
    if not name and not phone:
        return None
    return {'name': name or '—', 'phone': phone or ''}


def _status_history(order, lang, layout):
    settings = _section_settings(layout, STATUS_HISTORY)
    max_rows = int(settings.get('max_rows') or PDF_STATUS_HISTORY_MAX_ROWS)
    history_qs = order.status_history.select_related('changed_by').order_by('-created_at')[:max_rows]
    rows = []
    for entry in reversed(list(history_qs)):
        if entry.changed_by and order.customer_id and entry.changed_by_id == order.customer_id:
            changed_by = _label('Customer', lang)
        else:
            changed_by = (
                entry.changed_by.get_full_name() or entry.changed_by.username
                if entry.changed_by else '—'
            )
        rows.append({
            'when': _fmt_datetime(entry.created_at),
            'status': _choice_display(entry.status, order.ORDER_STATUS_CHOICES, lang),
            'changed_by': changed_by,
            'notes': _localized_note(entry.notes, lang),
        })
    return rows


def _tailor_payload(order):
    tailor = order.tailor
    if not tailor:
        return None
    shop_name = '—'
    contact = getattr(tailor, 'phone', None) or '—'
    try:
        profile = tailor.tailor_profile
        shop_name = profile.shop_name or _customer_display_name(tailor) or '—'
        contact = profile.contact_number or contact
    except Exception:
        pass
    return {
        'shop_name': shop_name,
        'name': _customer_display_name(tailor) or tailor.username,
        'contact': contact,
    }


def build_order_document_context(order, lang, layout, measurement_field_map=None):
    """Pure presentation context for the complete order document."""
    lang = lang if lang in ('en', 'ar', 'ur') else 'en'
    field_map = measurement_field_map if measurement_field_map is not None else _measurement_field_map()
    items, measurement_cols, measurement_rows = _build_items(order, lang, layout, field_map)
    person_settings = merge_section_settings(PERSON_ITEMS, _section_settings(layout, PERSON_ITEMS))

    rider_measurements = {}
    if isinstance(order.rider_measurements, dict) and order.rider_measurements:
        rider_measurements = {
            'measured_at': _fmt_datetime(order.measurement_taken_at) if order.measurement_taken_at else '',
            'cells': _build_measurement_cells(
                order.rider_measurements, field_map, lang, measurement_cols, measurement_rows,
            ),
            'notes': order.rider_measurements.get('notes') or '',
        }

    labels = {
        'receipt': _label('Order Receipt', lang),
        'customer': _label('CUSTOMER INFORMATION', lang),
        'name': _label('Name', lang),
        'service_mode': _label('Service Mode', lang),
        'measured_by': _label('Measured by', lang),
        'address': _label('Address', lang),
        'riders': _label('RIDERS', lang),
        'measurement_rider': _label('Measurement Rider', lang),
        'delivery_rider': _label('Delivery Rider', lang),
        'phone': _label('Phone', lang),
        'items_by_person': _label('ORDER ITEMS BY PERSON', lang),
        'person': _label('PERSON', lang),
        'fabric': _label('Fabric', lang),
        'qty': _label('Qty', lang),
        'ready': _label('Ready', lang),
        'yes': _label('Yes', lang),
        'no': _label('No', lang),
        'item_number': _label('Item #', lang),
        'sku': _label('SKU', lang),
        'fabric_qty': _label('Fabric Qty', lang),
        'fabric_photos': _label('Customer Fabric Photos', lang),
        'styles': _label('Styles:', lang),
        'comment': _label('Comment', lang),
        'instructions': _label('Instructions:', lang),
        'additional_notes': _label('Additional Notes:', lang),
        'rider_measurements': _label('RIDER MEASUREMENTS', lang),
        'measured_at': _label('Measured at:', lang),
        'order_summary': _label('ORDER SUMMARY', lang),
        'order_number': _label('Order Number', lang),
        'order_type': _label('Order Type', lang),
        'items_count': _label('Items Count', lang),
        'est_delivery': _label('Est. Delivery', lang),
        'actual_delivery': _label('Actual Delivery', lang),
        'appointment': _label('Appointment', lang),
        'stitching_done': _label('Stitching Done', lang),
        'shop_name': _label('Shop Name', lang),
        'tailor': _label('Tailor', lang),
        'contact': _label('Contact', lang),
        'notes': _label('NOTES & INSTRUCTIONS', lang),
        'special_instructions': _label('Special Instructions:', lang),
        'internal_notes': _label('Internal Notes:', lang),
        'status_history': _label('STATUS HISTORY', lang),
        'date_time': _label('Date & Time', lang),
        'status': _label('Status', lang),
        'changed_by': _label('Changed By', lang),
        'history_notes': _label('Notes', lang),
        'comments': _label('COMMENTS', lang),
        'generated': _label('Generated by Mgask Platform', lang),
        'order': _label('Order', lang),
        'page': _label('Page', lang),
        'status_label': _label('Status:', lang),
        'tailor_status_label': _label('Tailor Status:', lang),
        'placed_label': _label('Placed:', lang),
    }

    appointment = ''
    if order.appointment_date:
        appointment = _fmt_date(order.appointment_date)
        if order.appointment_time:
            appointment += f' at {order.appointment_time.strftime("%I:%M %p")}'

    return {
        'lang': lang,
        'is_rtl': is_rtl_language(lang),
        'fonts': _arabic_font_uris(),
        'layout': {
            'slug': layout.slug,
            'name': layout.name,
            'version': layout.version,
            'engine': layout.engine,
            'sections': [section.key for section in layout.sections],
            'person': person_settings,
        },
        'brand': 'MGASK',
        'generated_at': timezone.now().strftime('%d %b %Y, %I:%M %p'),
        'labels': labels,
        'order': {
            'id': order.id,
            'number': order.order_number,
            'status': _choice_display(order.status, order.ORDER_STATUS_CHOICES, lang),
            'tailor_status': _choice_display(order.tailor_status, order.TAILOR_STATUS_CHOICES, lang),
            'placed_at': _fmt_datetime(order.created_at),
            'type': _choice_display(order.order_type, order.ORDER_TYPE_CHOICES, lang),
            'service_mode': _choice_display(order.service_mode, order.SERVICE_MODE_CHOICES, lang),
            'items_count': str(order.items_count),
            'estimated_delivery': _fmt_date(order.estimated_delivery_date) if order.estimated_delivery_date else '',
            'actual_delivery': _fmt_date(order.actual_delivery_date) if order.actual_delivery_date else '',
            'appointment': appointment,
            'stitching_done': _fmt_date(order.stitching_completion_date) if order.stitching_completion_date else '',
            'special_instructions': order.special_instructions or '',
            'notes': order.notes or '',
        },
        'customer': {
            'name': _customer_display_name(order.customer) or '—',
            'address': _order_delivery_address(order) or '',
            'measured_by': _measurement_taken_by_name(order) or '',
        },
        'riders': {
            'measurement': _rider_payload(getattr(order, 'measurement_rider', None)),
            'delivery': _rider_payload(getattr(order, 'delivery_rider', None)),
        },
        'tailor': _tailor_payload(order),
        'items': items,
        'rider_measurements': rider_measurements,
        'measurement_cols': measurement_cols,
        'measurement_rows': measurement_rows,
        'status_history': _status_history(order, lang, layout),
        'escape': escape,
    }
