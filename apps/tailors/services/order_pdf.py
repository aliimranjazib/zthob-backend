# apps/tailors/services/order_pdf.py
"""
PDF generation service for tailor order download.
Supports English (default) and Arabic via Accept-Language header.
Requires: reportlab, arabic-reshaper, python-bidi
"""
import io
import os
import re
from decimal import Decimal
from xml.sax.saxutils import escape
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Image
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from django.utils import timezone

from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# ─── Arabic font registration ─────────────────────────────────────────────────
_FONTS_DIR = os.path.join(settings.BASE_DIR, 'fonts')
_AR_FONT_REGULAR = 'IBMPlexSansArabic-Regular'
_AR_FONT_BOLD    = 'IBMPlexSansArabic-Bold'

try:
    pdfmetrics.registerFont(TTFont(_AR_FONT_REGULAR, os.path.join(_FONTS_DIR, 'IBMPlexSansArabic-Regular.ttf')))
    pdfmetrics.registerFont(TTFont(_AR_FONT_BOLD,    os.path.join(_FONTS_DIR, 'IBMPlexSansArabic-Bold.ttf')))
    _ARABIC_FONT_AVAILABLE = True
except Exception as e:
    logger.warning("Failed to load Arabic fonts: %s", e)
    _ARABIC_FONT_AVAILABLE = False


# ─── Arabic text shaping helper ───────────────────────────────────────────────
_ARABIC_RE = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]')


def _contains_arabic(text):
    """Return True when text includes Arabic script characters."""
    if not text:
        return False
    return bool(_ARABIC_RE.search(str(text)))


def _shape_arabic(text):
    """
    Shape and reorder Arabic text for correct RTL rendering in ReportLab.
    Returns the visually-correct string.
    """
    if not text:
        return text
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        reshaped = arabic_reshaper.reshape(str(text))
        return get_display(reshaped)
    except Exception:
        return text


def _safe_text(value):
    """Escape text before inserting it into a ReportLab Paragraph."""
    if value is None:
        return '—'
    return escape(str(value))


def _format_user_text_html(text, lang='en'):
    """
    Prepare user-generated text for ReportLab Paragraphs.
    Arabic script is shaped and rendered with the Arabic font even in English PDFs.
    """
    if text is None or text == '':
        return '—'
    text = str(text)
    if _contains_arabic(text):
        if _ARABIC_FONT_AVAILABLE:
            shaped = _shape_arabic(text)
            return f'<font name="{_AR_FONT_REGULAR}">{_safe_text(shaped)}</font>'
        return _safe_text(text)
    if lang == 'ar' and _ARABIC_FONT_AVAILABLE:
        return _safe_text(_shape_arabic(text))
    return _safe_text(text)


def _customer_display_name(customer):
    if not customer:
        return None
    full_name = (customer.get_full_name() or '').strip()
    return full_name or customer.username


# ─── Translation dictionary ───────────────────────────────────────────────────
_AR_LABELS = {
    # Section headers
    'ORDER DETAILS':       'تفاصيل الطلب',
    'CUSTOMER DETAILS':    'بيانات العميل',
    'TAILOR DETAILS':      'بيانات الخياط',
    'NOTES & INSTRUCTIONS':'الملاحظات والتعليمات',
    'ORDER ITEMS':         'عناصر الطلب',
    'RIDER MEASUREMENTS':  'قياسات المندوب',
    'COMMENTS':            'التعليقات',
    'PRICING SUMMARY':     'ملخص التسعير',
    'PAYMENT SUMMARY':     'ملخص الدفع',
    'PAYMENT HISTORY':     'سجل المدفوعات',
    'STATUS HISTORY':      'سجل الحالة',
    # Order info labels
    'Order ID':            'معرف الطلب',
    'Order Number':        'رقم الطلب',
    'Order Type':          'نوع الطلب',
    'Service Mode':        'طريقة الخدمة',
    'Payment Method':      'طريقة الدفع',
    'Payment Status':      'حالة الدفع',
    'Payment Plan':        'خطة الدفع',
    'Payment Option':      'خيار الدفع',
    'Deposit Amount':      'مبلغ العربون',
    'Paid Amount':         'المبلغ المدفوع',
    'Remaining Amount':    'المبلغ المتبقي',
    'Amount Due':          'المبلغ المستحق',
    'Items Count':         'عدد العناصر',
    'Est. Delivery':       'التسليم المتوقع',
    'Actual Delivery':     'تاريخ التسليم',
    'Appointment':         'الموعد',
    'Stitching Done':      'تاريخ انتهاء الخياطة',
    # Customer labels
    'Customer Name':       'اسم العميل',
    'Phone':               'الهاتف',
    'Email':               'البريد الإلكتروني',
    'Delivery Addr.':      'عنوان التوصيل',
    'Extra Info':          'معلومات إضافية',
    'For (Family)':        'لصالح (عائلة)',
    'Relationship':        'صلة القرابة',
    'Customer':            'العميل',
    # Tailor labels
    'Shop Name':           'اسم المحل',
    'Tailor':              'الخياط',
    'Contact':             'التواصل',
    'Assigned Rider':      'المندوب المخصص',
    'Active Rider':        'المندوب الحالي',
    'Measurement Rider':   'مندوب القياس',
    'Delivery Rider':      'مندوب التوصيل',
    # Notes labels
    'Special Instructions:': 'تعليمات خاصة:',
    'Internal Notes:':       'ملاحظات داخلية:',
    # Items table headers
    'Item / Fabric':       'العنصر / القماش',
    'For':                 'لصالح',
    'Qty':                 'الكمية',
    'Unit Price':          'سعر الوحدة',
    'Total Price':         'السعر الإجمالي',
    'Ready':               'جاهز',
    'Comment':             'تعليق',
    # Statuses
    'Status:':             'الحالة:',
    'Tailor Status:':      'حالة الخياط:',
    'Placed:':             'تاريخ الطلب:',
    # Pricing
    'Subtotal':            'المجموع الفرعي',
    'Stitching Price':     'سعر الخياطة',
    'Tax':                 'الضريبة',
    'Delivery Fee':        'رسوم التوصيل',
    'Platform Fee':        'رسوم المنصة',
    'Express Fee':         'رسوم الخدمة السريعة',
    'TOTAL AMOUNT':        'المبلغ الإجمالي',
    'Payment Type':        'نوع الدفع',
    'Method':              'الطريقة',
    'Amount':              'المبلغ',
    'Collected By':        'تم التحصيل بواسطة',
    'Reference':           'المرجع',
    'No payment records found.': 'لا توجد سجلات دفع.',
    # History headers
    'Date & Time':         'التاريخ والوقت',
    'Status':              'الحالة',
    'Changed By':          'تم التغيير بواسطة',
    'Notes':               'الملاحظات',
    # Header
    'Order Receipt':       'إيصال الطلب',
    # Footer
    'Generated by Mgask Platform': 'تم الإنشاء بواسطة منصة مقاسك',
    'Order':               'الطلب',
    # Misc
    'No items found for this order.': 'لا توجد عناصر لهذا الطلب.',
    'Instructions:':       'التعليمات:',
    'Measurements:':       'القياسات:',
    'Styles:':             'الأنماط:',
    'Style Images:':       'صور الأنماط:',
    'N/A':                 'غير متاح',
    'Measured at:':        'تم القياس في:',
    'Measurement Service': 'خدمة القياس',
    'Yes':                 'نعم',
    'No':                  'لا',
    # Order values
    'Fabric Purchase Only': 'شراء قماش فقط',
    'Fabric + Stitching':  'قماش مع خياطة',
    'Measurement Service Only': 'خدمة قياس فقط',
    'Home Delivery':       'توصيل للمنزل',
    'Walk-In Service':     'زيارة المحل',
    'Cash on Delivery':    'الدفع عند الاستلام',
    'Credit Card':         'بطاقة ائتمان',
    'Bank Transfer':       'تحويل بنكي',
    'Pending':             'قيد الانتظار',
    'Partially Paid':      'مدفوع جزئياً',
    'Paid':                'مدفوع',
    'Refunded':            'مسترد',
    'Full Payment':        'دفع كامل',
    'Partial Payment':     'دفع جزئي',
    'Pay Later':           'الدفع لاحقاً',
    'Confirmed':           'مؤكد',
    'In Progress':         'قيد التنفيذ',
    'Ready for Delivery':  'جاهز للتوصيل',
    'Ready for Pickup':    'جاهز للاستلام',
    'Delivered':           'تم التوصيل',
    'Collected':           'تم الاستلام',
    'Cancelled':           'ملغي',
    'New':                 'جديد',
    'Accepted Order':      'تم قبول الطلب',
    'Started Stitching':   'بدأت الخياطة',
    'Finished Stitching':  'انتهت الخياطة',
    'Measurements Complete': 'اكتملت القياسات',
    'Record Measurements': 'تسجيل القياسات',
    'Deposit':             'عربون',
    'Remaining Balance':   'المبلغ المتبقي',
    'Refund':              'استرداد',
    'Adjustment':          'تعديل',
    'Failed':              'فشل',
    # Common measurement keys
    'Chest':               'الصدر',
    'Waist':               'الخصر',
    'Hips':                'الأرداف',
    'Shoulder':            'الكتف',
    'Sleeve':              'الكم',
    'Sleeve Length':       'طول الكم',
    'Length':              'الطول',
    'Neck':                'الرقبة',
    'Arm Hole':            'فتحة الإبط',
    'Cuff':                'الكم/الأسورة',
    'Thigh':               'الفخذ',
    'Inseam':              'طول الساق الداخلي',
    'Pocket':              'الجيب',
    'Collar':              'الياقة',
    'Back Width':          'عرض الظهر',
    'Front Width':         'عرض الصدر',
    'Bicep':               'العضلة',
    'Wrist':               'المعصم',
}


# ─── Brand colors ────────────────────────────────────────────────────────────
BRAND_PRIMARY   = colors.HexColor('#990404')   # Brand red
BRAND_ACCENT    = colors.HexColor('#C9A84C')   # Gold
BRAND_LIGHT     = colors.HexColor('#F5F5F5')   # Light grey
BRAND_MID       = colors.HexColor('#DDDDDD')   # Divider grey
BRAND_TEXT      = colors.HexColor('#333333')   # Main text
BRAND_SUBTEXT   = colors.HexColor('#666666')   # Secondary text
WHITE           = colors.white


def _styles(lang='en'):
    """Return a dict of named ParagraphStyles, RTL-aware when lang='ar'."""
    base = getSampleStyleSheet()
    is_ar = lang == 'ar' and _ARABIC_FONT_AVAILABLE

    font_regular = _AR_FONT_REGULAR if is_ar else 'Helvetica'
    font_bold    = _AR_FONT_BOLD    if is_ar else 'Helvetica-Bold'
    body_align   = TA_RIGHT if is_ar else TA_LEFT

    return {
        'title': ParagraphStyle(
            f'Title_{lang}',
            parent=base['Normal'],
            fontSize=22,
            fontName=font_bold,
            textColor=WHITE,
            alignment=TA_RIGHT if is_ar else TA_LEFT,
            spaceAfter=2,
        ),
        'subtitle': ParagraphStyle(
            f'Subtitle_{lang}',
            parent=base['Normal'],
            fontSize=10,
            fontName=font_regular,
            textColor=colors.HexColor('#CCCCCC'),
            alignment=TA_LEFT if is_ar else TA_LEFT,
        ),
        'section_header': ParagraphStyle(
            f'SectionHeader_{lang}',
            parent=base['Normal'],
            fontSize=9,
            fontName=font_bold,
            textColor=BRAND_ACCENT,
            spaceBefore=6,
            spaceAfter=3,
            alignment=body_align,
        ),
        'label': ParagraphStyle(
            f'Label_{lang}',
            parent=base['Normal'],
            fontSize=8,
            fontName=font_bold,
            textColor=BRAND_SUBTEXT,
            alignment=body_align,
        ),
        'value': ParagraphStyle(
            f'Value_{lang}',
            parent=base['Normal'],
            fontSize=9,
            fontName=font_regular,
            textColor=BRAND_TEXT,
            alignment=body_align,
        ),
        'small': ParagraphStyle(
            f'Small_{lang}',
            parent=base['Normal'],
            fontSize=7.5,
            fontName=font_regular,
            textColor=BRAND_SUBTEXT,
            alignment=body_align,
        ),
        'footer': ParagraphStyle(
            f'Footer_{lang}',
            parent=base['Normal'],
            fontSize=7,
            fontName=font_regular,
            textColor=BRAND_SUBTEXT,
            alignment=TA_CENTER,
        ),
        'table_header': ParagraphStyle(
            f'TableHeader_{lang}',
            parent=base['Normal'],
            fontSize=8,
            fontName=font_bold,
            textColor=WHITE,
            alignment=body_align,
        ),
        'table_cell': ParagraphStyle(
            f'TableCell_{lang}',
            parent=base['Normal'],
            fontSize=8,
            fontName=font_regular,
            textColor=BRAND_TEXT,
            alignment=body_align,
        ),
        'total_label': ParagraphStyle(
            f'TotalLabel_{lang}',
            parent=base['Normal'],
            fontSize=9,
            fontName=font_bold,
            textColor=BRAND_TEXT,
            alignment=TA_RIGHT,
        ),
        'total_value': ParagraphStyle(
            f'TotalValue_{lang}',
            parent=base['Normal'],
            fontSize=10,
            fontName=font_bold,
            textColor=BRAND_ACCENT,
            alignment=TA_RIGHT,
        ),
    }


def _fmt_date(dt):
    """Safely format a date/datetime to a readable string."""
    if dt is None:
        return '—'
    try:
        if hasattr(dt, 'strftime'):
            return dt.strftime('%d %b %Y')
        return str(dt)
    except Exception:
        return str(dt)


def _fmt_datetime(dt):
    """Safely format a datetime to readable string with time."""
    if dt is None:
        return '—'
    try:
        if hasattr(dt, 'strftime'):
            return dt.strftime('%d %b %Y, %I:%M %p')
        return str(dt)
    except Exception:
        return str(dt)


def _fmt_amount(value, currency='SAR'):
    """Format a decimal/float as currency string."""
    if value is None:
        return f'{currency} 0.00'
    try:
        return f'{currency} {float(value):,.2f}'
    except (TypeError, ValueError):
        return f'{currency} {value}'


def _choice_display(value, choices, lang='en'):
    """Return a localized display label for a Django choice value."""
    display = dict(choices).get(value, value or '—')
    return _t(display, lang) if lang == 'ar' else str(display)


def _localized_value(text, lang='en'):
    """Translate common display values when Arabic is requested."""
    return _t(text, lang) if lang == 'ar' else str(text or '—')


def _short_reference(reference):
    """Avoid exposing full gateway/manual payment references in the PDF."""
    if not reference:
        return '—'
    reference = str(reference)
    if len(reference) <= 8:
        return reference
    return f'...{reference[-6:]}'


def _is_positive_amount(value):
    try:
        return Decimal(value or '0.00') > Decimal('0.00')
    except Exception:
        return False


def _style_image_path(style):
    """Resolve a custom style payload image reference to a local media file."""
    if not isinstance(style, dict):
        return None

    path = style.get('asset_path') or style.get('image_url') or style.get('image')
    if not path:
        return None

    path = str(path).strip()
    media_url = getattr(settings, 'MEDIA_URL', '/media/')
    media_root = getattr(settings, 'MEDIA_ROOT', None)

    if path.startswith('http://') or path.startswith('https://'):
        marker = media_url if media_url.startswith('/') else f'/{media_url}'
        if marker in path:
            path = path.split(marker, 1)[1]
        else:
            return None

    if media_url and path.startswith(media_url):
        path = path[len(media_url):]
    path = path.lstrip('/')

    if os.path.isabs(path):
        candidate = path
    elif media_root:
        candidate = os.path.join(media_root, path)
    else:
        candidate = os.path.join(settings.BASE_DIR, path)

    return candidate if os.path.exists(candidate) else None


def _custom_style_image_grid(styles, page_w, s, lang='en'):
    """Build a compact grid of customer-selected custom style images."""
    image_cells = []
    for style in styles:
        image_path = _style_image_path(style)
        if not image_path:
            continue

        label = style.get('label') or style.get('style_type') or ''
        if style.get('style_type') and style.get('label'):
            label = f'{style.get("style_type", "").replace("_", " ").title()}: {style.get("label", "")}'

        try:
            img = Image(image_path, width=24 * mm, height=24 * mm, kind='proportional')
        except Exception as exc:
            logger.debug("Unable to add custom style image to PDF: %s", exc)
            continue

        image_cells.append([
            img,
            Paragraph(_format_user_text_html(label, lang), s['small']),
        ])

    if not image_cells:
        return None

    columns = 3
    rows = []
    for i in range(0, len(image_cells), columns):
        row = image_cells[i:i + columns]
        while len(row) < columns:
            row.append('')
        rows.append(row)

    cell_width = page_w / columns
    grid = Table(rows, colWidths=[cell_width] * columns, hAlign='LEFT')
    grid.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BACKGROUND', (0, 0), (-1, -1), WHITE),
        ('BOX', (0, 0), (-1, -1), 0.25, BRAND_MID),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, BRAND_MID),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    return grid


def _status_badge_color(status):
    """Return background color for status badge."""
    mapping = {
        'pending':           colors.HexColor('#FF9800'),
        'confirmed':         colors.HexColor('#2196F3'),
        'in_progress':       colors.HexColor('#9C27B0'),
        'ready_for_delivery':colors.HexColor('#009688'),
        'ready_for_pickup':  colors.HexColor('#009688'),
        'delivered':         colors.HexColor('#4CAF50'),
        'collected':         colors.HexColor('#4CAF50'),
        'cancelled':         colors.HexColor('#F44336'),
    }
    return mapping.get(status, BRAND_MID)


def _kv_table(rows, col_widths=None, lang='en'):
    """
    Build a compact key-value table.
    rows = list of (label_str, value_str) tuples.
    For RTL (Arabic), columns are swapped: value on left, label on right.
    """
    s = _styles(lang)
    is_ar = lang == 'ar'
    page_w = A4[0] - 40 * mm
    col_widths = col_widths or [page_w * 0.35, page_w * 0.65]

    if is_ar:
        col_widths = list(reversed(col_widths))
        
    data = []
    for row in rows:
        lbl = row[0]
        val = row[1]
        skip_trans = row[2] if len(row) > 2 else False
        
        lbl_p = Paragraph(_safe_text(_t(lbl, lang) if is_ar else lbl), s['label'])

        if not val:
            val_html = '—'
        elif skip_trans or lang == 'en':
            val_html = _format_user_text_html(val, lang)
        else:
            val_html = _safe_text(_t(val, lang))
        val_p = Paragraph(val_html, s['value'])

        if is_ar:
            data.append([val_p, lbl_p])
        else:
            data.append([lbl_p, val_p])

    tbl = Table(data, colWidths=col_widths, hAlign='RIGHT' if is_ar else 'LEFT')
    tbl.setStyle(TableStyle([
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING',    (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING',   (0, 0), (-1, -1), 0),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 6),
    ]))
    return tbl


def _rider_label(rider):
    if not rider:
        return None

    profile = getattr(rider, 'rider_profile', None)
    name = getattr(profile, 'full_name', None) or rider.get_full_name() or rider.username
    phone = getattr(profile, 'phone_number', None) or getattr(rider, 'phone', None)
    vehicle_type = getattr(profile, 'vehicle_type', None)

    details = [name]
    if phone:
        details.append(str(phone))
    if vehicle_type:
        details.append(str(vehicle_type))
    return ' | '.join(details)


def _t(text, lang):
    """Translate a label to Arabic and shape it for RTL rendering if lang='ar'."""
    if lang != 'ar':
        return str(text) if text else '—'
    arabic = _AR_LABELS.get(str(text), str(text)) if text else '—'
    return _shape_arabic(arabic)


def _item_recipient_display(item, order, lang='en'):
    """Return a clear 'For: …' line for the order item recipient."""
    for_label = _t('For', lang)
    if item.family_member_id and item.family_member:
        fm = item.family_member
        name = fm.name or '—'
        if fm.relationship:
            return f'{for_label}: {name} ({fm.relationship})'
        return f'{for_label}: {name}'

    customer_name = _customer_display_name(getattr(order, 'customer', None))
    if customer_name:
        return f'{for_label}: {customer_name}'
    return ''


def _measurement_field_map():
    """
    Return active measurement field metadata keyed by JSON field name.
    The PDF uses this as the source of truth for labels and ordering.
    """
    try:
        from apps.customization.models import MeasurementField
        fields = MeasurementField.objects.select_related('template').filter(
            is_active=True,
            template__is_active=True,
        ).order_by('template__display_order', 'display_order', 'name')
    except Exception as exc:
        logger.debug("Unable to load measurement field metadata for PDF: %s", exc)
        return {}

    field_map = {}
    for idx, field in enumerate(fields):
        field_map.setdefault(field.name, {
            'label_en': field.display_name or field.name.replace('_', ' ').title(),
            'label_ar': field.display_name_ar or field.display_name or field.name,
            'order': idx,
            'unit': getattr(field.template, 'default_unit', 'cm') or 'cm',
        })
    return field_map


def _format_measurement_pairs(measurements, lang='en', field_map=None):
    """Format measurement JSON into localized, consistently ordered label/value/unit tuples."""
    if not measurements or not isinstance(measurements, dict):
        return []

    field_map = field_map if field_map is not None else _measurement_field_map()
    formatted = []
    unknown_base_order = len(field_map) + 1000

    for idx, (key, value) in enumerate(measurements.items()):
        if key == 'title' or value in (None, '', 'null'):
            continue

        meta = field_map.get(key, {})
        fallback = str(key).replace('_', ' ').title()
        if lang == 'ar':
            raw_label = meta.get('label_ar') or _AR_LABELS.get(fallback, fallback)
            label = _shape_arabic(raw_label)
        else:
            label = meta.get('label_en') or fallback

        formatted.append((
            meta.get('order', unknown_base_order + idx),
            label,
            value,
            meta.get('unit', 'cm'),
        ))

    formatted.sort(key=lambda item: item[0])
    return [(label, value, unit) for _, label, value, unit in formatted]


def _measurements_grid(pairs, page_w, s, lang='en', title=''):
    """
    Render a list of (label, value) measurement pairs as a clean 3-column
    bordered card grid with an accent header row.

    Each card cell shows:
      ┌──────────────┐
      │  LABEL       │
      │  value cm    │
      └──────────────┘
    Numeric values automatically get a 'cm' unit appended.
    """
    is_ar = lang == 'ar'
    font_regular = _AR_FONT_REGULAR if (is_ar and _ARABIC_FONT_AVAILABLE) else 'Helvetica'
    font_bold    = _AR_FONT_BOLD    if (is_ar and _ARABIC_FONT_AVAILABLE) else 'Helvetica-Bold'
    align        = TA_RIGHT if is_ar else TA_LEFT

    lbl_style = ParagraphStyle(
        f'MeasLbl_{lang}', fontSize=7, fontName=font_bold,
        textColor=BRAND_ACCENT, alignment=align, spaceAfter=1,
    )
    val_style = ParagraphStyle(
        f'MeasVal_{lang}', fontSize=10, fontName=font_bold,
        textColor=BRAND_TEXT, alignment=align,
    )
    unit_style = ParagraphStyle(
        f'MeasUnit_{lang}', fontSize=7, fontName=font_regular,
        textColor=BRAND_SUBTEXT, alignment=align,
    )

    def _is_numeric(v):
        try:
            float(str(v).replace(',', ''))
            return True
        except ValueError:
            return False

    def _cell(lbl, val, unit=None):
        lbl_text = lbl if lang == 'ar' else str(lbl).upper()
        val_text = str(val)
        unit_text = unit if _is_numeric(val) else ''
        inner = [
            [Paragraph(_safe_text(lbl_text), lbl_style)],
            [Paragraph(_safe_text(val_text), val_style)],
        ]
        if unit_text:
            inner.append([Paragraph(_safe_text(unit_text), unit_style)])
        inner_tbl = Table(inner, colWidths=['100%'])
        inner_tbl.setStyle(TableStyle([
            ('TOPPADDING',    (0, 0), (-1, -1), 1),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ('LEFTPADDING',   (0, 0), (-1, -1), 0),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
        ]))
        return inner_tbl

    # Chunk pairs into rows of 3 cells each
    COLS = 3
    cell_w = page_w / COLS
    grid_rows = []

    # Optional title header row
    if title:
        title_text = _shape_arabic(title) if is_ar else title.upper()
        title_cell = Paragraph(_safe_text(title_text), ParagraphStyle(
            f'MeasTitle_{lang}', fontSize=8, fontName=font_bold,
            textColor=WHITE, alignment=TA_CENTER,
        ))
        title_row_tbl = Table([[title_cell]], colWidths=[page_w])
        title_row_tbl.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, -1), BRAND_PRIMARY),
            ('TOPPADDING',    (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING',   (0, 0), (-1, -1), 6),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 6),
        ]))
        # We'll prepend this manually below

    # Reverse order for RTL so pairs read right-to-left
    if is_ar:
        pairs = list(reversed(pairs))

    for i in range(0, len(pairs), COLS):
        chunk = pairs[i:i + COLS]
        # Pad with empty cells to fill the row
        while len(chunk) < COLS:
            chunk.append(('', ''))
        cells = []
        for pair in chunk:
            if not pair or not pair[0]:
                cells.append('')
                continue
            lbl = pair[0]
            val = pair[1]
            unit = pair[2] if len(pair) > 2 else 'cm'
            cells.append(_cell(lbl, val, unit))
        grid_rows.append(cells)

    if not grid_rows:
        return Paragraph('', s['value'])

    grid = Table(grid_rows, colWidths=[cell_w] * COLS)
    grid.setStyle(TableStyle([
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',    (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING',   (0, 0), (-1, -1), 8),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 8),
        ('GRID',          (0, 0), (-1, -1), 0.5, BRAND_MID),
        ('ROWBACKGROUNDS',(0, 0), (-1, -1), [WHITE, BRAND_LIGHT]),
        ('LINEABOVE',     (0, 0), (-1, 0),  1, BRAND_ACCENT),
        ('LINEBELOW',     (0, -1),(-1, -1), 1, BRAND_MID),
    ]))

    if title:
        # Wrap grid with title header in an outer table
        outer = Table(
            [[title_row_tbl], [grid]],
            colWidths=[page_w]
        )
        outer.setStyle(TableStyle([
            ('TOPPADDING',    (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('LEFTPADDING',   (0, 0), (-1, -1), 0),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
        ]))
        return outer

    return grid


def generate_order_pdf(order, lang='en') -> bytes:
    """
    Generate a professional PDF for a single order.

    Args:
        order: apps.orders.models.Order instance (with related objects pre-fetched or lazy).
        lang: Language code, 'en' (default) or 'ar' for Arabic RTL.

    Returns:
        bytes: Raw PDF file content.
    """
    is_ar = lang == 'ar'
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title=f'Order {order.order_number}',
        author='Mgask Platform',
    )

    s = _styles(lang)
    page_w = A4[0] - 40 * mm
    story = []
    measurement_fields = _measurement_field_map()

    # ── Header banner ─────────────────────────────────────────────────────────
    _receipt_label = _shape_arabic(_AR_LABELS['Order Receipt']) if is_ar else 'Order Receipt'
    _font_bold = _AR_FONT_BOLD if (is_ar and _ARABIC_FONT_AVAILABLE) else 'Helvetica-Bold'
    if is_ar:
        header_data = [[
            Paragraph(
                f'<b>{_receipt_label}</b><br/><font color="#CCCCCC">{order.order_number}</font>',
                ParagraphStyle(f'hr_{lang}', parent=s['subtitle'], alignment=TA_RIGHT, fontSize=10,
                               textColor=WHITE, fontName=_font_bold)
            ),
            Paragraph(_shape_arabic('مقاسك'), s['title']),
        ]]
    else:
        header_data = [[
            Paragraph('MGASK', s['title']),
            Paragraph(
                f'<b>Order Receipt</b><br/><font color="#CCCCCC">{order.order_number}</font>',
                ParagraphStyle(f'hr_{lang}', parent=s['subtitle'], alignment=TA_RIGHT, fontSize=10,
                               textColor=WHITE, fontName=_font_bold)
            ),
        ]]
    header_tbl = Table(header_data, colWidths=[page_w * 0.5, page_w * 0.5])
    header_tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), BRAND_PRIMARY),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',    (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('LEFTPADDING',   (0, 0), (0, -1),  10),
        ('RIGHTPADDING',  (-1, 0), (-1, -1), 10),
        ('ROUNDEDCORNERS', [4, 4, 4, 4]),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 5 * mm))

    # ── Status strip ──────────────────────────────────────────────────────────
    status_display = _choice_display(order.status, order.ORDER_STATUS_CHOICES, lang)
    tailor_status_display = _choice_display(order.tailor_status, order.TAILOR_STATUS_CHOICES, lang) if order.tailor_status else _t('N/A', lang)
    status_color = _status_badge_color(order.status)
    _sb_font = _AR_FONT_BOLD if (is_ar and _ARABIC_FONT_AVAILABLE) else 'Helvetica-Bold'

    _status_lbl  = _t('Status:', lang)
    _tailor_lbl  = _t('Tailor Status:', lang)
    _placed_lbl  = _t('Placed:', lang)

    status_data = [[
        Paragraph(f'{_safe_text(_status_lbl)} <b>{_safe_text(status_display)}</b>',
                  ParagraphStyle(f'sb_{lang}', parent=s['value'], fontSize=9, textColor=WHITE, fontName=_sb_font,
                                 alignment=TA_RIGHT if is_ar else TA_LEFT)),
        Paragraph(f'{_safe_text(_tailor_lbl)} <b>{_safe_text(tailor_status_display)}</b>',
                  ParagraphStyle(f'sb2_{lang}', parent=s['value'], fontSize=9, textColor=WHITE, fontName=_sb_font,
                                 alignment=TA_CENTER)),
        Paragraph(f'{_safe_text(_placed_lbl)} <b>{_safe_text(_fmt_datetime(order.created_at))}</b>',
                  ParagraphStyle(f'sb3_{lang}', parent=s['value'], fontSize=9, textColor=WHITE, fontName=_sb_font,
                                 alignment=TA_LEFT if is_ar else TA_RIGHT)),
    ]]
    if is_ar:
        status_data[0].reverse()
    status_tbl = Table(status_data, colWidths=[page_w / 3] * 3)
    status_tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), status_color),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',    (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING',   (0, 0), (-1, -1), 8),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 8),
    ]))
    story.append(status_tbl)
    story.append(Spacer(1, 5 * mm))

    # ── Order Info ────────────────────────────────────────────────────────────
    # Order Info
    order_type_display = _choice_display(order.order_type, order.ORDER_TYPE_CHOICES, lang)
    service_mode_display = _choice_display(order.service_mode, order.SERVICE_MODE_CHOICES, lang)

    order_info_rows = [
        ('Order ID',         str(order.id)),
        ('Order Number',     order.order_number, True),
        ('Order Type',       order_type_display, True),
        ('Service Mode',     service_mode_display, True),
        ('Items Count',      str(order.items_count)),
    ]
    if order.estimated_delivery_date:
        order_info_rows.append(('Est. Delivery', _fmt_date(order.estimated_delivery_date)))
    if order.actual_delivery_date:
        order_info_rows.append(('Actual Delivery', _fmt_date(order.actual_delivery_date)))
    if order.appointment_date:
        appt = _fmt_date(order.appointment_date)
        if order.appointment_time:
            appt += f' at {order.appointment_time.strftime("%I:%M %p")}'
        order_info_rows.append(('Appointment', appt))
    if order.stitching_completion_date:
        order_info_rows.append(('Stitching Done', _fmt_date(order.stitching_completion_date)))

    story.append(Paragraph(_t('ORDER DETAILS', lang), s['section_header']))
    story.append(HRFlowable(width=page_w, color=BRAND_ACCENT, thickness=0.5, spaceAfter=4))
    story.append(_kv_table(order_info_rows, col_widths=[page_w * 0.30, page_w * 0.70], lang=lang))
    story.append(Spacer(1, 5 * mm))

    # ── Tailor Info ───────────────────────────────────────────────────────────
    tailor = order.tailor
    if tailor:
        story.append(Paragraph(_t('TAILOR DETAILS', lang), s['section_header']))
        story.append(HRFlowable(width=page_w, color=BRAND_ACCENT, thickness=0.5, spaceAfter=4))

        tailor_name = tailor.get_full_name() or tailor.username
        shop_name = '—'
        tailor_contact = getattr(tailor, 'phone', None) or '—'

        try:
            profile = tailor.tailor_profile
            shop_name = profile.shop_name or tailor_name
            tailor_contact = profile.contact_number or tailor_contact
        except Exception:
            pass

        tailor_rows = [
            ('Shop Name',  shop_name),
            ('Tailor',     tailor_name),
            ('Contact',    tailor_contact, True),
        ]
        rider_rows = [
            ('Measurement Rider', _rider_label(getattr(order, 'measurement_rider', None)), True),
            ('Delivery Rider', _rider_label(getattr(order, 'delivery_rider', None)), True),
        ]
        active_rider = getattr(order, 'rider', None)
        assigned_rider = getattr(order, 'assigned_rider', None)
        role_specific_rider_ids = {
            rider.id
            for rider in [getattr(order, 'measurement_rider', None), getattr(order, 'delivery_rider', None)]
            if rider
        }
        if active_rider and active_rider.id not in role_specific_rider_ids:
            rider_rows.append(('Active Rider', _rider_label(active_rider), True))
        if assigned_rider and assigned_rider.id not in role_specific_rider_ids and assigned_rider != active_rider:
            rider_rows.append(('Assigned Rider', _rider_label(assigned_rider), True))
        tailor_rows.extend(row for row in rider_rows if row[1])

        story.append(_kv_table(tailor_rows, lang=lang))
        story.append(Spacer(1, 4 * mm))

    # ── Special instructions / notes ──────────────────────────────────────────
    if order.special_instructions or order.notes:
        story.append(Paragraph(_t('NOTES & INSTRUCTIONS', lang), s['section_header']))
        story.append(HRFlowable(width=page_w, color=BRAND_ACCENT, thickness=0.5, spaceAfter=4))
        if order.special_instructions:
            _si_label = _t('Special Instructions:', lang)
            story.append(Paragraph(
                f'<b>{_safe_text(_si_label)}</b> {_format_user_text_html(order.special_instructions, lang)}',
                s['value'],
            ))
            story.append(Spacer(1, 2 * mm))
        if order.notes:
            _n_label = _t('Internal Notes:', lang)
            story.append(Paragraph(
                f'<b>{_safe_text(_n_label)}</b> {_format_user_text_html(order.notes, lang)}',
                s['value'],
            ))
        story.append(Spacer(1, 4 * mm))

    # ── Order Items table ─────────────────────────────────────────────────────
    story.append(Paragraph(_t('ORDER ITEMS', lang), s['section_header']))
    story.append(HRFlowable(width=page_w, color=BRAND_ACCENT, thickness=0.5, spaceAfter=4))

    items = list(order.order_items.select_related('fabric', 'family_member').all())

    if items:
        col_widths_items = [
            page_w * 0.65,  # Item / Fabric
            page_w * 0.15,  # Qty
            page_w * 0.20,  # Status
        ]

        item_headers = [
            Paragraph(_t('Item / Fabric', lang), s['table_header']),
            Paragraph(_t('Qty', lang), s['table_header']),
            Paragraph(_t('Ready', lang), s['table_header']),
        ]
        if is_ar:
            item_headers.reverse()
        item_rows = [item_headers]

        for item in items:
            fabric_name = item.fabric.name if item.fabric else _localized_value('Measurement Service', lang)
            fabric_sku = f'SKU: {item.fabric.sku}' if item.fabric and item.fabric.sku else ''
            recipient_line = _item_recipient_display(item, order, lang)
            fabric_parts = []
            if recipient_line:
                fabric_parts.append(
                    f'<font color="#990404"><b>{_format_user_text_html(recipient_line, lang)}</b></font>'
                )
            fabric_parts.append(_format_user_text_html(fabric_name, lang))
            if fabric_sku:
                fabric_parts.append(f'<font color="#888888" size="7">{_safe_text(fabric_sku)}</font>')
            fabric_cell = Paragraph('<br/>'.join(fabric_parts), s['table_cell'])

            is_ready = ('✓ ' + (_shape_arabic('نعم') if is_ar else 'Yes')) if item.is_ready \
                  else ('✗ ' + (_shape_arabic('لا')  if is_ar else 'No'))
            ready_color = colors.HexColor('#4CAF50') if item.is_ready else colors.HexColor('#F44336')
            _item_font_bold = _AR_FONT_BOLD if (is_ar and _ARABIC_FONT_AVAILABLE) else 'Helvetica-Bold'

            row = [
                fabric_cell,
                Paragraph(_safe_text(str(item.quantity)), s['table_cell']),
                Paragraph(is_ready, ParagraphStyle(
                    f'is_ready_{lang}', parent=s['table_cell'],
                    textColor=ready_color, fontName=_item_font_bold
                )),
            ]
            if is_ar:
                row.reverse()
            item_rows.append(row)

            # Extra info rows (Instructions, Measurements, Styles)
            # We use an empty list for spanned columns [Content, '', '', '']
            
            # 1. Custom instructions row
            if item.custom_instructions:
                _instr_label = _t('Instructions:', lang)
                instr_p = Paragraph(
                    f'<b>{_safe_text(_instr_label)}</b> {_format_user_text_html(item.custom_instructions, lang)}',
                    s['small'],
                )
                item_rows.append([instr_p, '', ''])

            # 2. Measurements row — rendered as a professional grid
            if item.measurements and isinstance(item.measurements, dict):
                meas_pairs = _format_measurement_pairs(item.measurements, lang, measurement_fields)
                if meas_pairs:
                    meas_title = item.measurements.get('title', '')
                    grid = _measurements_grid(meas_pairs, page_w, s, lang, title=meas_title)
                    item_rows.append([grid, '', ''])

            # 3. Custom style images (text list removed — images + labels are enough)
            if item.custom_styles and isinstance(item.custom_styles, list):
                style_image_grid = _custom_style_image_grid(item.custom_styles, page_w, s, lang)
                if style_image_grid:
                    styles_heading = Paragraph(f'<b>{_safe_text(_t("Styles:", lang))}</b>', s['small'])
                    item_rows.append([styles_heading, '', ''])
                    item_rows.append([style_image_grid, '', ''])

        items_tbl = Table(item_rows, colWidths=col_widths_items, repeatRows=1)
        
        # Build style list
        tbl_style = [
            ('BACKGROUND',    (0, 0), (-1, 0),  BRAND_PRIMARY),
            ('TOPPADDING',    (0, 0), (-1, 0),  6),
            ('BOTTOMPADDING', (0, 0), (-1, 0),  6),
            ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
            ('GRID',          (0, 0), (-1, -1), 0.3, BRAND_MID),
            ('LINEBELOW',     (0, 0), (-1, 0),  1,   BRAND_ACCENT),
        ]

        # Apply SPAN and special styling for info rows
        for idx, row in enumerate(item_rows):
            if idx == 0: continue # Header
            # Check if this is an info row (has only one real content in index 0 or index -1 for RTL)
            # In our case we always put content in index 0 then reverse, so content is at an edge column.
            # But the SPAN logic in ReportLab always uses absolute indices 0..N.
            
            # Simple heuristic: if every column after the first is empty, it's a spanned row.
            if row[1] == '' and row[2] == '':
                tbl_style.append(('SPAN', (0, idx), (-1, idx)))
                # Set background for measurement grid to distinguish it
                if not isinstance(row[0], Paragraph):
                    tbl_style.append(('BACKGROUND', (0, idx), (-1, idx), BRAND_LIGHT))
                    tbl_style.append(('TOPPADDING',    (0, idx), (-1, idx), 2))
                    tbl_style.append(('BOTTOMPADDING', (0, idx), (-1, idx), 2))
                else:
                    # It's a text info row (Instructions/Styles)
                    tbl_style.append(('LEFTPADDING', (0, idx), (-1, idx), 15))
                    tbl_style.append(('TOPPADDING',    (0, idx), (-1, idx), 2))
                    tbl_style.append(('BOTTOMPADDING', (0, idx), (-1, idx), 2))
            else:
                # Main item row
                bg_color = WHITE if (idx % 2 == 1) else BRAND_LIGHT
                tbl_style.append(('BACKGROUND', (0, idx), (-1, idx), bg_color))

        items_tbl.setStyle(TableStyle(tbl_style))
        story.append(items_tbl)
    else:
        story.append(Paragraph(_t('No items found for this order.', lang), s['value']))

    story.append(Spacer(1, 6 * mm))

    # ── Order-level measurements (rider measurements) ─────────────────────────
    if order.rider_measurements and isinstance(order.rider_measurements, dict) and order.rider_measurements:
        story.append(Paragraph(_t('RIDER MEASUREMENTS', lang), s['section_header']))
        story.append(HRFlowable(width=page_w, color=BRAND_ACCENT, thickness=0.5, spaceAfter=4))
        if order.measurement_taken_at:
            story.append(Paragraph(
                f'<i>{_safe_text(_t("Measured at:", lang))} {_safe_text(_fmt_datetime(order.measurement_taken_at))}</i>',
                s['small']
            ))
            story.append(Spacer(1, 2 * mm))
        meas_pairs = _format_measurement_pairs(order.rider_measurements, lang, measurement_fields)
        story.append(_measurements_grid(meas_pairs, page_w, s, lang))
        story.append(Spacer(1, 5 * mm))
    # ── Status History ────────────────────────────────────────────────────────
    history_qs = order.status_history.select_related('changed_by').order_by('created_at')[:20]
    history = list(history_qs)

    if history:
        story.append(Paragraph(_t('STATUS HISTORY', lang), s['section_header']))
        story.append(HRFlowable(width=page_w, color=BRAND_ACCENT, thickness=0.5, spaceAfter=4))

        hist_headers = [
            Paragraph(_t('Date & Time', lang), s['table_header']),
            Paragraph(_t('Status', lang), s['table_header']),
            Paragraph(_t('Changed By', lang), s['table_header']),
            Paragraph(_t('Notes', lang), s['table_header']),
        ]
        if is_ar:
            hist_headers.reverse()
        hist_rows = [hist_headers]

        for h in history:
            if h.changed_by and order.customer_id and h.changed_by_id == order.customer_id:
                changed_by = _AR_LABELS['Customer'] if is_ar else 'Customer'
            else:
                changed_by = h.changed_by.get_full_name() or h.changed_by.username if h.changed_by else '—'
            hist_row = [
                Paragraph(_fmt_datetime(h.created_at), s['small']),
                Paragraph(h.get_status_display(), s['small']),
                Paragraph(_format_user_text_html(changed_by, lang), s['small']),
                Paragraph(_format_user_text_html(h.notes or '—', lang), s['small']),
            ]
            if is_ar:
                hist_row.reverse()
            hist_rows.append(hist_row)

        hist_tbl = Table(
            hist_rows,
            colWidths=[page_w * 0.25, page_w * 0.20, page_w * 0.22, page_w * 0.33],
            repeatRows=1
        )
        hist_tbl.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, 0),  BRAND_PRIMARY),
            ('TOPPADDING',    (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING',   (0, 0), (-1, -1), 5),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 5),
            ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
            ('GRID',          (0, 0), (-1, -1), 0.3, BRAND_MID),
            ('LINEBELOW',     (0, 0), (-1, 0),  1,   BRAND_ACCENT),
            ('ROWBACKGROUNDS',(0, 1), (-1, -1), [WHITE, BRAND_LIGHT]),
        ]))
        story.append(hist_tbl)
        story.append(Spacer(1, 5 * mm))

    # ── Comments ──────────────────────────────────────────────────────────────
    story.append(Paragraph(_t('COMMENTS', lang), s['section_header']))
    story.append(HRFlowable(width=page_w, color=BRAND_ACCENT, thickness=0.5, spaceAfter=4))
    comments_tbl = Table([['']], colWidths=[page_w], rowHeights=[28 * mm])
    comments_tbl.setStyle(TableStyle([
        ('BOX',           (0, 0), (-1, -1), 0.7, BRAND_MID),
        ('BACKGROUND',    (0, 0), (-1, -1), WHITE),
        ('TOPPADDING',    (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING',   (0, 0), (-1, -1), 8),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 8),
    ]))
    story.append(comments_tbl)
    story.append(Spacer(1, 5 * mm))

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(HRFlowable(width=page_w, color=BRAND_MID, thickness=0.5, spaceAfter=4))
    generated_time = timezone.now().strftime('%d %b %Y, %I:%M %p')
    if is_ar:
        _gen_label = _shape_arabic(_AR_LABELS['Generated by Mgask Platform'])
        _order_label = _shape_arabic(_AR_LABELS['Order'])
        footer_text = f'{_order_label} {order.order_number}  ·  {generated_time}  ·  {_gen_label}'
    else:
        footer_text = f'Generated by Mgask Platform  ·  {generated_time}  ·  Order {order.order_number}'
    story.append(Paragraph(footer_text, s['footer']))

    # Build PDF
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
