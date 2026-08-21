# apps/tailors/services/order_pdf.py
"""
PDF generation service for tailor order download.
Supports English (default) and Arabic via Accept-Language header.
Requires: reportlab, arabic-reshaper, python-bidi
"""
import io
import os
import re
import unicodedata
from decimal import Decimal
from urllib.parse import urlparse
from xml.sax.saxutils import escape
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Image,
    KeepTogether,
)
from reportlab.platypus.doctemplate import BaseDocTemplate, PageTemplate, Frame, NextPageTemplate
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from django.utils import timezone

from django.conf import settings
import logging

from zthob.languages import is_rtl_language
from .pdf_labels_ur import PDF_LABELS_UR

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
_SCRIPT_RUN_RE = re.compile(
    r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]+|'
    r'[^\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]+',
    re.UNICODE,
)
_LRM = '\u200e'
# Strip invisible bidi/control chars that break shaping when copied from mobile keyboards.
_RTL_STRIP_RE = re.compile(r'[\u200b-\u200f\u202a-\u202e\u2066-\u2069\ufeff]')
# Collapse runs of whitespace (keep single spaces between words).
_WHITESPACE_RUN_RE = re.compile(r'\s+')
# Coordinate-only address strings (lat, lng) are not useful on tailor PDFs.
_COORD_ONLY_RE = re.compile(
    r'^\s*-?\d+(?:\.\d+)?\s*,\s*-?\d+(?:\.\d+)?\s*$'
)

_reshaper_config = None


def _get_reshaper_config():
    """Lazy-load arabic-reshaper config with ligature support enabled."""
    global _reshaper_config
    if _reshaper_config is not None:
        return _reshaper_config
    try:
        import arabic_reshaper
        config = arabic_reshaper.config_for_arabic()
        config.delete_tatweel = False
        config.support_ligatures = True
        config.use_unshaped_instead_of_individual_forms = False
        _reshaper_config = config
    except Exception:
        _reshaper_config = False
    return _reshaper_config


def _repair_spaced_script_text(text):
    """
    Repair Arabic/Urdu text where mobile keyboards inserted spaces between letters.
    Example: 'ج ا ن' -> 'جان' while preserving real word boundaries.
    """
    if not text or not _contains_arabic(text):
        return text

    tokens = str(text).split(' ')
    repaired = []
    buffer = []

    def _flush_buffer():
        if not buffer:
            return
        if len(buffer) >= 2 and all(len(token) == 1 and _contains_arabic(token) for token in buffer):
            repaired.append(''.join(buffer))
        else:
            repaired.extend(buffer)
        buffer.clear()

    for token in tokens:
        if len(token) == 1 and _contains_arabic(token):
            buffer.append(token)
        else:
            _flush_buffer()
            if token:
                repaired.append(token)
    _flush_buffer()
    return ' '.join(repaired)


def _normalize_rtl_text(text):
    """Normalize Arabic/Urdu user text before shaping."""
    if text is None:
        return ''
    normalized = unicodedata.normalize('NFC', str(text))
    normalized = _RTL_STRIP_RE.sub('', normalized)
    normalized = _WHITESPACE_RUN_RE.sub(' ', normalized).strip()
    return _repair_spaced_script_text(normalized)


def _contains_arabic(text):
    """Return True when text includes Arabic script characters."""
    if not text:
        return False
    return bool(_ARABIC_RE.search(str(text)))


def _is_rtl(lang):
    return is_rtl_language(lang)


def _labels_for(lang):
    if lang == 'ur':
        return PDF_LABELS_UR
    if lang == 'ar':
        return _AR_LABELS
    return {}


def _brand_title(lang):
    if lang == 'ar':
        return _shape_arabic('مقاسك')
    if lang == 'ur':
        return _shape_arabic('مقاسک')
    return 'MGASK'


def _shape_arabic(text):
    """
    Shape and reorder Arabic text for correct RTL rendering in ReportLab.
    Returns the visually-correct string. Applied exactly once per text run.
    """
    if not text:
        return text
    logical = _normalize_rtl_text(text)
    if not logical:
        return logical
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display

        config = _get_reshaper_config()
        if config:
            reshaped = arabic_reshaper.reshape(logical, configuration=config)
        else:
            reshaped = arabic_reshaper.reshape(logical)
        return get_display(reshaped)
    except Exception:
        return logical


def _translate_label(text, lang):
    """Return translated label in logical order (not shaped)."""
    if not _is_rtl(lang):
        return str(text) if text else '—'
    labels = _labels_for(lang)
    return labels.get(str(text), str(text)) if text else '—'


def _safe_text(value):
    """Escape text before inserting it into a ReportLab Paragraph."""
    if value is None:
        return '—'
    return escape(str(value))


def _format_user_text_html(text, lang='en', *, reshape=True):
    """
    Prepare user-generated text for ReportLab Paragraphs.
    Arabic runs are shaped individually so Latin text in mixed strings stays readable.
    Set reshape=False when the value was already shaped (e.g. via _t()).
    """
    if text is None or text == '':
        return '—'
    text = _normalize_rtl_text(text)
    runs = _SCRIPT_RUN_RE.findall(text)
    if not runs:
        return _safe_text(text)

    has_arabic = any(_contains_arabic(run) for run in runs)
    if not has_arabic:
        return _safe_text(text)

    has_latin = any(run.strip() and not _contains_arabic(run) for run in runs)
    if not has_latin:
        display = _shape_arabic(text) if reshape else text
        if _ARABIC_FONT_AVAILABLE:
            return f'<font name="{_AR_FONT_REGULAR}">{_safe_text(display)}</font>'
        return _safe_text(display)

    parts = []
    for run in runs:
        if _contains_arabic(run):
            display = _shape_arabic(run) if reshape else run
            if _ARABIC_FONT_AVAILABLE:
                parts.append(f'<font name="{_AR_FONT_REGULAR}">{_safe_text(display)}</font>')
            else:
                parts.append(_safe_text(display))
        else:
            latin = f'{_LRM}{run}{_LRM}' if _is_rtl(lang) else run
            parts.append(_safe_text(latin))
    return ''.join(parts)


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
    'CUSTOMER INFORMATION':'معلومات العميل',
    'RIDERS':              'المندوبون',
    'ORDER ITEMS BY PERSON':'عناصر الطلب حسب الشخص',
    'ORDER SUMMARY':       'ملخص الطلب',
    'PERSON':              'الشخص',
    'Name':                'الاسم',
    'Address':             'العنوان',
    'Fabric':              'القماش',
    'SKU':                 'رمز المنتج',
    'Item #':              'العنصر رقم',
    'Page':                'صفحة',
    'Self':                'العميل نفسه',
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
    'Measured by':         'تم القياس بواسطة',
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
    'Reference Photos':    'صور مرجعية',
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
    'Additional Notes:':   'ملاحظات إضافية:',
    'Measurements:':       'القياسات:',
    'Styles:':             'الأنماط:',
    'Style Images:':       'صور الأنماط:',
    'N/A':                 'غير متاح',
    'Measured at:':        'تم القياس في:',
    'Measurement Service': 'خدمة القياس',
    'Customer Fabric':     'قماش العميل',
    'Fabric Qty':          'كمية القماش',
    'Customer Fabric Photos': 'صور قماش العميل',
    'Stitching Only':      'خياطة فقط',
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
    # Measurement fields (fallback when DB has no Arabic label)
    'Placket Length':      'طول الكمر',
    'Pocket Height':       'ارتفاع الجيب',
    'Bottom Width':        'عرض الأسفل',
    'Chest Front':         'الصدر الأمامي',
    'Back Length':         'طول الظهر',
    'Neck Width':          'عرض الرقبة',
    'Chest Side':          'الصدر الجانبي',
    'Chest Back':          'الصدر الخلفي',
    # Status history notes
    'Order created':       'تم إنشاء الطلب',
    'Payment status changed from pending to paid': 'تم تغيير حالة الدفع من قيد الانتظار إلى مدفوع',
    'Payment status changed from partially paid to paid': 'تم تغيير حالة الدفع من مدفوع جزئياً إلى مدفوع',
    'Payment status changed from pending to partially paid': 'تم تغيير حالة الدفع من قيد الانتظار إلى مدفوع جزئياً',
}


# ─── Brand colors ────────────────────────────────────────────────────────────
BRAND_PRIMARY   = colors.HexColor('#990404')   # Brand red
BRAND_ACCENT    = colors.HexColor('#C9A84C')   # Gold
BRAND_LIGHT     = colors.HexColor('#F5F5F5')   # Light grey
BRAND_MID       = colors.HexColor('#DDDDDD')   # Divider grey
BRAND_TEXT      = colors.HexColor('#333333')   # Main text
BRAND_SUBTEXT   = colors.HexColor('#666666')   # Secondary text
WHITE           = colors.white

# Compact single-page layout
PDF_MARGIN_H = 10 * mm
PDF_MARGIN_V = 8 * mm
PDF_SECTION_SPACER = 2.5 * mm
PDF_ITEM_SPACER = 1.5 * mm
PDF_PERSON_BLOCK_SPACER = 5 * mm
PDF_MEASUREMENT_COLS = 5
PDF_MEASUREMENT_ROWS = 4
PDF_STYLE_GRID_COLS = 5
PDF_STYLE_THUMB_SIZE = 13 * mm
PDF_REF_THUMB_SIZE = 11 * mm
PDF_COMMENT_BOX_HEIGHT = 8 * mm
PDF_STATUS_HISTORY_MAX_ROWS = 4
PDF_HR_SPACE_AFTER = 1
PDF_PAGE_NUMBER_OFFSET = 4 * mm
PDF_REPEAT_HEADER_H = 11 * mm
PDF_FIRST_PAGE_TOP = PDF_MARGIN_V + PDF_PAGE_NUMBER_OFFSET
PDF_LATER_PAGE_TOP = PDF_FIRST_PAGE_TOP + PDF_REPEAT_HEADER_H


def _pdf_page_width():
    return A4[0] - (2 * PDF_MARGIN_H)


def _styles(lang='en'):
    """Return a dict of named ParagraphStyles, RTL-aware for Arabic/Urdu."""
    base = getSampleStyleSheet()
    is_rtl = _is_rtl(lang) and _ARABIC_FONT_AVAILABLE

    font_regular = _AR_FONT_REGULAR if is_rtl else 'Helvetica'
    font_bold    = _AR_FONT_BOLD    if is_rtl else 'Helvetica-Bold'
    body_align   = TA_RIGHT if is_rtl else TA_LEFT

    return {
        'title': ParagraphStyle(
            f'Title_{lang}',
            parent=base['Normal'],
            fontSize=16,
            fontName=font_bold,
            textColor=WHITE,
            alignment=TA_RIGHT if is_rtl else TA_LEFT,
            spaceAfter=0,
            leading=18,
        ),
        'subtitle': ParagraphStyle(
            f'Subtitle_{lang}',
            parent=base['Normal'],
            fontSize=8,
            fontName=font_regular,
            textColor=colors.HexColor('#CCCCCC'),
            alignment=TA_LEFT,
            leading=10,
        ),
        'section_header': ParagraphStyle(
            f'SectionHeader_{lang}',
            parent=base['Normal'],
            fontSize=7.5,
            fontName=font_bold,
            textColor=BRAND_ACCENT,
            spaceBefore=2,
            spaceAfter=1,
            alignment=body_align,
            leading=9,
        ),
        'label': ParagraphStyle(
            f'Label_{lang}',
            parent=base['Normal'],
            fontSize=6.5,
            fontName=font_bold,
            textColor=BRAND_SUBTEXT,
            alignment=body_align,
            leading=8,
        ),
        'value': ParagraphStyle(
            f'Value_{lang}',
            parent=base['Normal'],
            fontSize=7,
            fontName=font_regular,
            textColor=BRAND_TEXT,
            alignment=body_align,
            leading=8,
        ),
        'small': ParagraphStyle(
            f'Small_{lang}',
            parent=base['Normal'],
            fontSize=6.5,
            fontName=font_regular,
            textColor=BRAND_SUBTEXT,
            alignment=body_align,
            leading=8,
        ),
        'style_card_label': ParagraphStyle(
            f'StyleCardLabel_{lang}',
            parent=base['Normal'],
            fontSize=6,
            fontName=font_bold,
            textColor=BRAND_TEXT,
            alignment=TA_CENTER,
            leading=7,
            spaceBefore=1,
        ),
        'style_card_comment': ParagraphStyle(
            f'StyleCardComment_{lang}',
            parent=base['Normal'],
            fontSize=5.5,
            fontName=font_regular,
            textColor=BRAND_SUBTEXT,
            alignment=TA_CENTER,
            leading=7,
            spaceBefore=0,
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
            fontSize=6.5,
            fontName=font_bold,
            textColor=WHITE,
            alignment=body_align,
            leading=8,
        ),
        'table_cell': ParagraphStyle(
            f'TableCell_{lang}',
            parent=base['Normal'],
            fontSize=6.5,
            fontName=font_regular,
            textColor=BRAND_TEXT,
            alignment=body_align,
            leading=8,
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
    """Return a localized display label for a Django choice value (logical order)."""
    display = dict(choices).get(value, value or '—')
    if _is_rtl(lang):
        return _translate_label(str(display), lang)
    return str(display)


def _localized_value(text, lang='en'):
    """Translate common display values for RTL PDFs (logical order)."""
    if _is_rtl(lang):
        return _translate_label(str(text or '—'), lang)
    return str(text or '—')


def _inline_value_html(value, lang='en'):
    """Shape a localized or user value once for inline Paragraph HTML."""
    if value is None or value == '':
        return '—'
    if not _is_rtl(lang):
        return _safe_text(value)
    return _format_user_text_html(value, lang)


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


def _resolve_media_file_path(raw_path):
    """Resolve a stored/API media reference to an existing local file path."""
    if not raw_path:
        return None

    path = str(raw_path).strip()
    if not path:
        return None

    media_root = getattr(settings, 'MEDIA_ROOT', None)
    if not media_root:
        return None

    if path.startswith(('http://', 'https://')):
        path = urlparse(path).path

    path = path.lstrip('/')
    if path.startswith('api/media/'):
        path = path[len('api/media/'):]
    elif path.startswith('media/'):
        path = path[len('media/'):]

    candidate = os.path.join(media_root, path)
    return candidate if os.path.exists(candidate) else None


def _style_image_path(style):
    """Resolve a custom style payload image reference to a local media file."""
    if not isinstance(style, dict):
        return None

    path = style.get('asset_path') or style.get('image_url') or style.get('image')
    resolved = _resolve_media_file_path(path)
    if resolved:
        return resolved
    return _style_image_from_db(style)


def _style_reference_image_paths(style):
    """Resolve customer-uploaded reference photos for a style selection."""
    if not isinstance(style, dict):
        return []

    refs = style.get('reference_images') or []
    if not isinstance(refs, list):
        return []

    paths = []
    for ref in refs:
        resolved = _resolve_media_file_path(ref)
        if resolved:
            paths.append(resolved)
    return paths[:4]


def _style_image_from_db(style):
    """Resolve style image via CustomStyle when stored asset_path is missing on disk."""
    if not isinstance(style, dict):
        return None

    try:
        from apps.customization.models import CustomStyle, CustomStyleCategory

        style_type = style.get('style_type')
        if not style_type:
            return None

        category = CustomStyleCategory.objects.filter(name=style_type).first()
        if not category:
            return None

        queryset = CustomStyle.objects.filter(
            category=category,
            is_active=True,
        ).order_by('display_order', 'id')

        label = style.get('label')
        if label:
            match = queryset.filter(name=label).first()
            if match and match.image:
                path = match.image.path
                if os.path.exists(path):
                    return path

        index = style.get('index')
        if index is not None:
            styles = list(queryset)
            try:
                style_obj = styles[int(index)]
            except (IndexError, TypeError, ValueError):
                style_obj = None
            if style_obj and style_obj.image:
                path = style_obj.image.path
                if os.path.exists(path):
                    return path
    except Exception as exc:
        logger.debug("Unable to resolve custom style image from DB: %s", exc)

    return None


_STYLE_COMMENT_MAX_CHARS = 36


def _truncate_style_comment(text, max_chars=_STYLE_COMMENT_MAX_CHARS):
    """Keep long customer comments readable without blowing up grid cell height."""
    normalized = ' '.join(str(text or '').split())
    if not normalized:
        return ''
    if len(normalized) <= max_chars:
        return normalized
    return f'{normalized[: max_chars - 1].rstrip()}…'


def _custom_style_label_text(style):
    """Plain-text style label for card captions."""
    label = style.get('label') or style.get('style_type') or ''
    if style.get('style_type') and style.get('label'):
        label = f'{style.get("style_type", "").replace("_", " ").title()}: {style.get("label", "")}'
    return str(label).strip()


def _format_label_html(text, lang):
    """Translate and shape a static label once for Paragraph HTML."""
    if not _is_rtl(lang):
        return _safe_text(text)
    return _format_user_text_html(_translate_label(text, lang), lang)


def _custom_style_label_html(style, lang='en'):
    label = _custom_style_label_text(style)
    if not label:
        return None
    return _format_user_text_html(label, lang)


def _custom_style_comment_html(style, lang='en'):
    comment = _truncate_style_comment((style.get('text') or '').strip())
    if not comment:
        return None
    comment_lbl = _translate_label('Comment', lang)
    # Shape label + body together so RTL labels (تعليق) are not reversed in the PDF.
    return _format_user_text_html(f'{comment_lbl}: {comment}', lang)


def _custom_style_caption_html(style, lang='en'):
    """Combined caption for simple text-only layouts."""
    parts = [p for p in (_custom_style_label_html(style, lang), _custom_style_comment_html(style, lang)) if p]
    return '<br/>'.join(parts)


def _custom_style_reference_images_row(ref_paths, inner_width, s, lang='en'):
    """Render a compact row of customer reference photos under the catalog style image."""
    images = []
    thumb_size = PDF_REF_THUMB_SIZE
    col_width = thumb_size + 3 * mm
    for ref_path in ref_paths:
        try:
            images.append(Image(ref_path, width=thumb_size, height=thumb_size, kind='proportional'))
        except Exception as exc:
            logger.debug("Unable to add style reference image to PDF card: %s", exc)

    if not images:
        return None

    ref_table = Table([images], colWidths=[col_width] * len(images))
    ref_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    return ref_table


def _custom_style_card(style, cell_width, s, lang='en'):
    """One centered mini-card: catalog image, reference photos, label, optional comment."""
    label_html = _custom_style_label_html(style, lang)
    comment_html = _custom_style_comment_html(style, lang)
    image_path = _style_image_path(style)
    reference_paths = _style_reference_image_paths(style)
    if not label_html and not comment_html and not image_path and not reference_paths:
        return None

    inner_width = max(cell_width - 4, PDF_REF_THUMB_SIZE + 2 * mm)
    rows = []

    if image_path:
        try:
            img = Image(image_path, width=PDF_STYLE_THUMB_SIZE, height=PDF_STYLE_THUMB_SIZE, kind='proportional')
            rows.append([img])
        except Exception as exc:
            logger.debug("Unable to add custom style image to PDF card: %s", exc)

    if reference_paths:
        ref_row = _custom_style_reference_images_row(reference_paths, inner_width, s, lang)
        if ref_row:
            rows.append([ref_row])

    if label_html:
        rows.append([Paragraph(label_html, s['style_card_label'])])
    if comment_html:
        rows.append([Paragraph(comment_html, s['style_card_comment'])])

    card = Table(rows, colWidths=[inner_width])
    card.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
    ]))
    return card


def _custom_style_image_grid(styles, page_w, s, lang='en'):
    """Build a compact grid of customer-selected custom style cards."""
    columns = PDF_STYLE_GRID_COLS
    cell_width = page_w / columns
    cards = []
    for style in styles:
        card = _custom_style_card(style, cell_width, s, lang)
        if card:
            cards.append(card)

    if not cards:
        return None

    rows = []
    for i in range(0, len(cards), columns):
        row = cards[i:i + columns]
        while len(row) < columns:
            row.append('')
        rows.append(row)

    grid = Table(rows, colWidths=[cell_width] * columns, hAlign='LEFT')
    grid.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BACKGROUND', (0, 0), (-1, -1), WHITE),
        ('BOX', (0, 0), (-1, -1), 0.25, BRAND_MID),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, BRAND_MID),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
    ]))
    return grid


def _custom_style_labels_fallback(styles, s, lang='en'):
    """Text-only fallback when style image files are unavailable."""
    blocks = []
    for style in styles:
        label_html = _custom_style_label_html(style, lang)
        comment_html = _custom_style_comment_html(style, lang)
        if not label_html and not comment_html:
            continue

        style_rows = []
        if label_html:
            style_rows.append([Paragraph(label_html, s['label'])])
        if comment_html:
            style_rows.append([Paragraph(comment_html, s['small'])])
        block = Table(style_rows, colWidths=[160 * mm])
        block.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT' if _is_rtl(lang) else 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        blocks.append(block)

    if not blocks:
        return None

    if len(blocks) == 1:
        return blocks[0]

    stack = Table([[block] for block in blocks], colWidths=[160 * mm])
    stack.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    return stack


def _custom_style_section(styles, page_w, s, lang='en'):
    """Prefer image grid; fall back to labels when images are missing."""
    grid = _custom_style_image_grid(styles, page_w, s, lang)
    if grid:
        return grid
    return _custom_style_labels_fallback(styles, s, lang)


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
    is_rtl = _is_rtl(lang)
    page_w = _pdf_page_width()
    col_widths = col_widths or [page_w * 0.35, page_w * 0.65]

    if is_rtl:
        col_widths = list(reversed(col_widths))
        
    data = []
    for row in rows:
        lbl = row[0]
        val = row[1]
        skip_trans = row[2] if len(row) > 2 else False
        
        lbl_p = Paragraph(_safe_text(_t(lbl, lang) if is_rtl else lbl), s['label'])

        if not val:
            val_html = '—'
        elif skip_trans:
            val_html = _format_user_text_html(val, lang)
        elif lang == 'en':
            val_html = _format_user_text_html(val, lang)
        else:
            val_html = _format_user_text_html(_translate_label(val, lang), lang)
        val_p = Paragraph(val_html, s['value'])

        if is_rtl:
            data.append([val_p, lbl_p])
        else:
            data.append([lbl_p, val_p])

    tbl = Table(data, colWidths=col_widths, hAlign='RIGHT' if is_rtl else 'LEFT')
    tbl.setStyle(TableStyle([
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING',    (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('LEFTPADDING',   (0, 0), (-1, -1), 0),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
    ]))
    return tbl


def _rider_contact_details(rider):
    """Return rider display name and phone as separate values."""
    if not rider:
        return None, None

    profile = getattr(rider, 'rider_profile', None)
    name = getattr(profile, 'full_name', None) or rider.get_full_name() or rider.username
    phone = getattr(profile, 'phone_number', None) or getattr(rider, 'phone', None)
    return name, str(phone) if phone else None


def _rider_label(rider):
    if not rider:
        return None

    name, phone = _rider_contact_details(rider)
    profile = getattr(rider, 'rider_profile', None)
    vehicle_type = getattr(profile, 'vehicle_type', None)

    details = [name]
    if phone:
        details.append(phone)
    if vehicle_type:
        details.append(str(vehicle_type))
    return ' | '.join(details)


def _customer_phone(order):
    customer = getattr(order, 'customer', None)
    if not customer:
        return None
    return getattr(customer, 'phone', None)


def _measurement_taken_by_name(order):
    """Return who recorded measurements, if that is known for this order."""
    if not getattr(order, 'measurement_taken_at', None):
        return None

    rider = getattr(order, 'measurement_rider', None)
    if rider:
        name, _phone = _rider_contact_details(rider)
        if name:
            return name

    if getattr(order, 'service_mode', None) != 'walk_in':
        return None

    tailor = getattr(order, 'tailor', None)
    if not tailor:
        return None
    try:
        shop_name = (tailor.tailor_profile.shop_name or '').strip()
    except Exception:
        shop_name = ''
    return _customer_display_name(tailor) or shop_name or None


def _is_coordinate_address(text):
    return bool(_COORD_ONLY_RE.match(str(text or '').strip()))


def _clean_address_candidate(text):
    candidate = str(text or '').strip()
    if not candidate or _is_coordinate_address(candidate):
        return None
    return candidate


def _order_delivery_address(order):
    """Return a human-readable delivery address for the order."""
    candidates = []

    formatted = getattr(order, 'delivery_formatted_address', None)
    if formatted:
        candidates.append(formatted)

    parts = []
    for field in ('delivery_street', 'delivery_city', 'delivery_extra_info'):
        value = getattr(order, field, None)
        if value:
            parts.append(str(value))
    if parts:
        candidates.append(', '.join(parts))

    addr = getattr(order, 'delivery_address', None)
    if addr:
        if getattr(addr, 'address', None):
            candidates.append(addr.address)
        addr_parts = [p for p in (getattr(addr, 'street', None), getattr(addr, 'city', None)) if p]
        if addr_parts:
            candidates.append(', '.join(addr_parts))

    for candidate in candidates:
        cleaned = _clean_address_candidate(candidate)
        if cleaned:
            return cleaned
    return None


def _t(text, lang):
    """Translate a label for RTL languages and shape it for PDF rendering."""
    if not _is_rtl(lang):
        return str(text) if text else '—'
    return _shape_arabic(_translate_label(text, lang))


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


def _format_recipient_html(item, order, lang='en'):
    """Render recipient line without corrupting mixed Arabic/English text."""
    for_label = _t('For', lang)
    if item.family_member_id and item.family_member:
        fm = item.family_member
        name_html = _format_user_text_html(fm.name or '—', lang)
        if fm.relationship:
            rel_html = _format_user_text_html(fm.relationship, lang)
            body = f'{name_html} ({rel_html})'
        else:
            body = name_html
    else:
        customer_name = _customer_display_name(getattr(order, 'customer', None)) or '—'
        body = _format_user_text_html(customer_name, lang)

    label = _safe_text(for_label)
    if _is_rtl(lang):
        return f'<font color="#990404"><b>{label}: {_LRM}{body}{_LRM}</b></font>'
    return f'<font color="#990404"><b>{label}: {body}</b></font>'


def _localized_note(note, lang='en'):
    """Translate known status-history notes for RTL PDFs."""
    if not note or not _is_rtl(lang):
        return note or '—'
    return _labels_for(lang).get(str(note), str(note))


def _append_measurement_notes(block, measurements, page_w, s, lang):
    """Render optional rider/tailor notes stored on a measurements payload."""
    if not measurements or not isinstance(measurements, dict):
        return
    meas_notes = str(measurements.get('notes') or '').strip()
    if not meas_notes:
        return
    notes_label = _t('Additional Notes:', lang)
    block.append(Paragraph(
        f'<b>{_safe_text(notes_label)}</b> {_format_user_text_html(meas_notes, lang)}',
        s['small'],
    ))
    block.append(Spacer(1, PDF_ITEM_SPACER))


def _measurement_field_map():
    """
    Return active measurement field metadata keyed by JSON field name.
    The PDF uses this as the source of truth for labels. Field order follows the payload.
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
            'label_ur': field.display_name_ur or field.display_name or field.name,
            'order': idx,
            'display_order': field.display_order,
            'pdf_grid_row': getattr(field, 'pdf_grid_row', None),
            'pdf_grid_col': getattr(field, 'pdf_grid_col', None),
            'unit': getattr(field.template, 'default_unit', 'cm') or 'cm',
        })
    return field_map


def _format_measurement_pairs(measurements, lang='en', field_map=None):
    """Format measurement JSON into localized label/value/unit tuples, preserving payload order."""
    if not measurements or not isinstance(measurements, dict):
        return []

    from apps.orders.measurement_utils import ordered_measurement_keys

    field_map = field_map if field_map is not None else _measurement_field_map()
    formatted = []

    for key in ordered_measurement_keys(measurements):
        value = measurements.get(key)
        if value in (None, '', 'null'):
            continue

        meta = field_map.get(key, {})
        fallback = str(key).replace('_', ' ').title()
        if _is_rtl(lang):
            label_attr = 'label_ur' if lang == 'ur' else 'label_ar'
            labels = _labels_for(lang)
            raw_label = meta.get(label_attr) or meta.get('label_en') or fallback
            if not _contains_arabic(raw_label):
                raw_label = labels.get(raw_label, labels.get(fallback, raw_label))
            label = _shape_arabic(_normalize_rtl_text(raw_label))
        else:
            label = meta.get('label_en') or fallback

        snapshot_unit = measurements.get('unit') if isinstance(measurements, dict) else None
        formatted.append((
            label,
            value,
            snapshot_unit or meta.get('unit', 'cm'),
        ))

    return formatted


def _single_measurement_pair(key, value, measurements, field_map, lang):
    """Format one measurement key into (label, value, unit)."""
    meta = field_map.get(key, {})
    fallback = str(key).replace('_', ' ').title()
    if _is_rtl(lang):
        label_attr = 'label_ur' if lang == 'ur' else 'label_ar'
        labels = _labels_for(lang)
        raw_label = meta.get(label_attr) or meta.get('label_en') or fallback
        if not _contains_arabic(raw_label):
            raw_label = labels.get(raw_label, labels.get(fallback, raw_label))
        label = _shape_arabic(_normalize_rtl_text(raw_label))
    else:
        label = meta.get('label_en') or fallback
    unit = measurements.get('unit') if isinstance(measurements, dict) else None
    return label, value, unit or meta.get('unit', 'cm')


def _positioned_measurement_cells(measurements, field_map, lang, cols, rows, show_all_slots=True):
    """Map grid positions to label/value/unit tuples for ReportLab rendering."""
    from apps.documents.measurement_grid import build_measurement_grid_cells

    cells = build_measurement_grid_cells(
        measurements,
        field_map,
        lang,
        cols,
        rows,
        show_all_slots=show_all_slots,
    )
    placed = {}
    for cell in cells:
        if not cell.get('label'):
            continue
        value = cell['value'] if cell.get('has_value') else '—'
        unit = cell.get('unit', 'cm') if cell.get('has_value') else ''
        placed[(cell['row'], cell['col'])] = (cell['label'], value, unit)
    return placed


def _measurements_grid_positioned(
    measurements,
    field_map,
    page_w,
    s,
    lang='en',
    title='',
    cols=None,
    rows=None,
):
    """Render measurements in a fixed rows x cols grid using pdf_grid_row/col metadata."""
    cols = cols or PDF_MEASUREMENT_COLS
    rows = rows or PDF_MEASUREMENT_ROWS
    placed = _positioned_measurement_cells(measurements, field_map, lang, cols, rows)
    if not placed:
        return None

    is_rtl = _is_rtl(lang)
    font_bold = _AR_FONT_BOLD if (is_rtl and _ARABIC_FONT_AVAILABLE) else 'Helvetica-Bold'
    align = TA_RIGHT if is_rtl else TA_LEFT
    lbl_style = ParagraphStyle(
        f'MeasLblPos_{lang}', fontSize=5.5, fontName=font_bold,
        textColor=BRAND_ACCENT, alignment=align, spaceAfter=0, leading=6,
    )
    val_style = ParagraphStyle(
        f'MeasValPos_{lang}', fontSize=7.5, fontName=font_bold,
        textColor=BRAND_TEXT, alignment=align, leading=8,
    )

    def _is_numeric(v):
        try:
            float(str(v).replace(',', ''))
            return True
        except ValueError:
            return False

    def _cell(lbl, val, unit=None):
        if not lbl:
            return ''
        lbl_text = str(lbl).upper() if not is_rtl else str(lbl)
        val_text = str(val)
        unit_text = unit if _is_numeric(val) else ''
        if unit_text:
            val_text = f'{val_text} {unit_text}'
        inner = [
            [Paragraph(_safe_text(lbl_text), lbl_style)],
            [Paragraph(_safe_text(val_text), val_style)],
        ]
        inner_tbl = Table(inner, colWidths=['100%'])
        inner_tbl.setStyle(TableStyle([
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        return inner_tbl

    cell_w = page_w / cols
    grid_rows = []
    for row in range(1, rows + 1):
        cells = []
        for col in range(1, cols + 1):
            pair = placed.get((row, col))
            if pair:
                cells.append(_cell(pair[0], pair[1], pair[2] if len(pair) > 2 else 'cm'))
            else:
                cells.append('')
        grid_rows.append(cells)

    grid = Table(grid_rows, colWidths=[cell_w] * cols)
    grid.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('GRID', (0, 0), (-1, -1), 0.5, BRAND_MID),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [WHITE, BRAND_LIGHT]),
        ('LINEABOVE', (0, 0), (-1, 0), 1, BRAND_ACCENT),
        ('LINEBELOW', (0, -1), (-1, -1), 1, BRAND_MID),
    ]))

    if title:
        title_text = _shape_arabic(title) if is_rtl else title.upper()
        title_cell = Paragraph(_safe_text(title_text), ParagraphStyle(
            f'MeasTitlePos_{lang}', fontSize=6.5, fontName=font_bold,
            textColor=WHITE, alignment=TA_CENTER, leading=8,
        ))
        title_row_tbl = Table([[title_cell]], colWidths=[page_w])
        title_row_tbl.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), BRAND_PRIMARY),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]))
        outer = Table([[title_row_tbl], [grid]], colWidths=[page_w])
        outer.setStyle(TableStyle([
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        return outer

    return grid


def _measurement_grid_rows(pairs, cols, is_rtl=False):
    """
    Fill the measurement grid top-to-bottom, then the next column.

    English starts at the top-left. Arabic starts at the top-right so
    reading down the rightmost column follows payload order.
    """
    pairs = list(pairs)
    if not pairs or cols <= 0:
        return []

    empty = ('', '')
    rows_count = (len(pairs) + cols - 1) // cols
    grid = [[empty for _ in range(cols)] for _ in range(rows_count)]

    for index, pair in enumerate(pairs):
        col = index // rows_count
        row = index % rows_count
        if is_rtl:
            col = cols - 1 - col
        grid[row][col] = pair
    return grid


def _measurements_grid(pairs, page_w, s, lang='en', title=''):
    """
    Render measurement pairs as a dense multi-column bordered card grid.
    """
    is_rtl = _is_rtl(lang)
    font_regular = _AR_FONT_REGULAR if (is_rtl and _ARABIC_FONT_AVAILABLE) else 'Helvetica'
    font_bold    = _AR_FONT_BOLD    if (is_rtl and _ARABIC_FONT_AVAILABLE) else 'Helvetica-Bold'
    align        = TA_RIGHT if is_rtl else TA_LEFT

    lbl_style = ParagraphStyle(
        f'MeasLbl_{lang}', fontSize=5.5, fontName=font_bold,
        textColor=BRAND_ACCENT, alignment=align, spaceAfter=0, leading=6,
    )
    val_style = ParagraphStyle(
        f'MeasVal_{lang}', fontSize=7.5, fontName=font_bold,
        textColor=BRAND_TEXT, alignment=align, leading=8,
    )

    def _is_numeric(v):
        try:
            float(str(v).replace(',', ''))
            return True
        except ValueError:
            return False

    def _cell(lbl, val, unit=None):
        lbl_text = str(lbl).upper() if not _is_rtl(lang) else str(lbl)
        val_text = str(val)
        unit_text = unit if _is_numeric(val) else ''
        if unit_text:
            val_text = f'{val_text} {unit_text}'
        inner = [
            [Paragraph(_safe_text(lbl_text), lbl_style)],
            [Paragraph(_safe_text(val_text), val_style)],
        ]
        inner_tbl = Table(inner, colWidths=['100%'])
        inner_tbl.setStyle(TableStyle([
            ('TOPPADDING',    (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('LEFTPADDING',   (0, 0), (-1, -1), 0),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
        ]))
        return inner_tbl

    COLS = PDF_MEASUREMENT_COLS
    cell_w = page_w / COLS
    grid_rows = []

    # Optional title header row
    if title:
        title_text = _shape_arabic(title) if is_rtl else title.upper()
        title_cell = Paragraph(_safe_text(title_text), ParagraphStyle(
            f'MeasTitle_{lang}', fontSize=6.5, fontName=font_bold,
            textColor=WHITE, alignment=TA_CENTER, leading=8,
        ))
        title_row_tbl = Table([[title_cell]], colWidths=[page_w])
        title_row_tbl.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, -1), BRAND_PRIMARY),
            ('TOPPADDING',    (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LEFTPADDING',   (0, 0), (-1, -1), 4),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
        ]))
        # We'll prepend this manually below

    for chunk in _measurement_grid_rows(pairs, COLS, is_rtl=is_rtl):
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
        ('TOPPADDING',    (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING',   (0, 0), (-1, -1), 3),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 3),
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


def _item_fabric_display_name(item, order, lang):
    """Catalog fabric name, or a type-specific fallback when the customer brought fabric."""
    if item.fabric:
        return item.fabric.name
    if getattr(order, 'order_type', None) == 'stitching_only':
        return _localized_value('Customer Fabric', lang)
    return _localized_value('Measurement Service', lang)


def _item_fabric_label_html(item, order, lang):
    """Compact fabric/recipient line for priority measurement/style sections."""
    fabric_name_html = _format_user_text_html(_item_fabric_display_name(item, order, lang), lang)
    fabric_sku = f'SKU: {item.fabric.sku}' if item.fabric and item.fabric.sku else ''
    fabric_parts = []
    recipient_html = _format_recipient_html(item, order, lang)
    if recipient_html:
        fabric_parts.append(recipient_html)
    fabric_parts.append(fabric_name_html)
    if fabric_sku:
        fabric_parts.append(f'<font color="#888888" size="6">{_safe_text(fabric_sku)}</font>')
    return '<br/>'.join(fabric_parts)


def _person_header_detail_text(item, order):
    if item.family_member_id and item.family_member:
        fm = item.family_member
        name = fm.name or '—'
        if fm.relationship:
            return f'{name} ({fm.relationship})'
        return name
    return _customer_display_name(getattr(order, 'customer', None)) or '—'


def _person_header_text(item, order, lang, person_index):
    """Plain-text person block title, e.g. PERSON 1 — Ali (son)."""
    person_lbl = _translate_label('PERSON', lang)
    detail = _person_header_detail_text(item, order)
    return f'{person_lbl} {person_index} — {detail}'


def _person_header_bar(item, order, page_w, s, lang, person_index):
    """Accent bar heading for each person block."""
    is_rtl = _is_rtl(lang)
    font_bold = _AR_FONT_BOLD if (is_rtl and _ARABIC_FONT_AVAILABLE) else 'Helvetica-Bold'
    detail = _person_header_detail_text(item, order)
    if is_rtl:
        person_lbl = _safe_text(_t('PERSON', lang))
        detail_html = _format_user_text_html(detail, lang)
        body_html = f'{person_lbl} {person_index} — {_LRM}{detail_html}{_LRM}'
    else:
        body_html = _safe_text(f'PERSON {person_index} — {detail}'.upper())
    cell = Paragraph(
        body_html,
        ParagraphStyle(
            f'PersonHdr_{lang}',
            parent=s['section_header'],
            fontSize=7.5,
            fontName=font_bold,
            textColor=WHITE,
            alignment=TA_CENTER,
            leading=9,
        ),
    )
    tbl = Table([[cell]], colWidths=[page_w])
    tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), BRAND_PRIMARY),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    return tbl


def _item_detail_cell(label, value_html, s, lang):
    lbl = _safe_text(_t(label, lang))
    return Paragraph(f'<b>{lbl}:</b> {value_html}', s['small'])


def _item_details_table(item, order, page_w, s, lang, item_index):
    """Aligned item metadata table for each person block."""
    fabric_name_html = _format_user_text_html(_item_fabric_display_name(item, order, lang), lang)

    ready_val = _format_user_text_html(
        _localized_value('Yes', lang) if item.is_ready else _localized_value('No', lang),
        lang,
    )
    qty_html = _safe_text(str(item.quantity))
    item_num_html = _safe_text(str(item_index))

    col_w = page_w / 3
    row1 = [
        _item_detail_cell('Fabric', fabric_name_html, s, lang),
        _item_detail_cell('Qty', qty_html, s, lang),
        _item_detail_cell('Ready', ready_val, s, lang),
    ]
    row2_cells = [
        _item_detail_cell('Item #', item_num_html, s, lang),
    ]
    if item.fabric and item.fabric.sku:
        row2_cells.append(_item_detail_cell('SKU', _safe_text(item.fabric.sku), s, lang))
    if getattr(item, 'customer_fabric_quantity', None) is not None:
        fabric_qty = f'{item.customer_fabric_quantity} m'
        row2_cells.append(_item_detail_cell('Fabric Qty', _safe_text(fabric_qty), s, lang))
    while len(row2_cells) < 3:
        row2_cells.append(Paragraph('', s['small']))
    row2 = row2_cells

    if _is_rtl(lang):
        row1.reverse()
        row2.reverse()

    tbl = Table([row1, row2], colWidths=[col_w] * 3)
    tbl.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BACKGROUND', (0, 0), (-1, -1), BRAND_LIGHT),
        ('BOX', (0, 0), (-1, -1), 0.35, BRAND_MID),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, BRAND_MID),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    return tbl


def _customer_fabric_image_paths(item):
    """Resolve attached customer fabric photos to local files."""
    images = getattr(item, 'customer_fabric_images', None)
    if images is None:
        return []

    paths = []
    for image in images.all():
        raw_path = image.image.name if getattr(image, 'image', None) else None
        resolved = _resolve_media_file_path(raw_path)
        if resolved:
            paths.append(resolved)
    return paths[:4]


def _customer_fabric_images_table(item, page_w, s, lang):
    """Compact row of customer-provided fabric photos."""
    paths = _customer_fabric_image_paths(item)
    if not paths:
        return None

    images = []
    thumb_size = PDF_STYLE_THUMB_SIZE
    col_width = thumb_size + 4 * mm
    for path in paths:
        try:
            images.append(Image(path, width=thumb_size, height=thumb_size, kind='proportional'))
        except Exception as exc:
            logger.debug("Unable to add customer fabric image to PDF: %s", exc)

    if not images:
        return None

    title = Paragraph(_safe_text(_t('Customer Fabric Photos', lang)), s['small'])
    img_table = Table([images], colWidths=[col_width] * len(images))
    img_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    wrapper = Table([[title], [img_table]], colWidths=[page_w])
    wrapper.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    return wrapper


def _item_details_html(item, order, lang, item_index):
    """Fabric, quantity, SKU, item number, and ready status for a person block."""
    fabric_name_html = _format_user_text_html(_item_fabric_display_name(item, order, lang), lang)

    fabric_lbl = _safe_text(_t('Fabric', lang))
    qty_lbl = _safe_text(_t('Qty', lang))
    item_num_lbl = _safe_text(_t('Item #', lang))
    ready_lbl = _safe_text(_t('Ready', lang))
    ready_val = _safe_text(_t('Yes', lang) if item.is_ready else _t('No', lang))

    parts = [
        f'<b>{fabric_lbl}:</b> {fabric_name_html}',
        f'<b>{qty_lbl}:</b> {_safe_text(str(item.quantity))}',
        f'<b>{item_num_lbl}</b> {_safe_text(str(item_index))}',
        f'<b>{ready_lbl}:</b> {ready_val}',
    ]
    if item.fabric and item.fabric.sku:
        sku_lbl = _safe_text(_t('SKU', lang))
        parts.insert(2, f'<b>{sku_lbl}:</b> {_safe_text(item.fabric.sku)}')
    if getattr(item, 'customer_fabric_quantity', None) is not None:
        fabric_qty_lbl = _safe_text(_t('Fabric Qty', lang))
        parts.insert(2, f'<b>{fabric_qty_lbl}:</b> {_safe_text(str(item.customer_fabric_quantity))} m')
    return ' &nbsp;|&nbsp; '.join(parts)


def _rider_info_cell(rider, lang, s):
    """Rider name with phone on a separate line."""
    name, phone = _rider_contact_details(rider)
    if not name:
        return Paragraph(_safe_text('—'), s['value'])

    phone_html = ''
    if phone:
        phone_lbl = _safe_text(_t('Phone', lang))
        phone_html = f'<br/><font size="6">{phone_lbl}: {_safe_text(phone)}</font>'
    return Paragraph(
        f'<b>{_format_user_text_html(name, lang)}</b>{phone_html}',
        s['value'],
    )


def _build_customer_section(order, page_w, s, lang):
    """Customer name, service mode, and who took measurements in aligned columns."""
    story = []
    story.append(Paragraph(_t('CUSTOMER INFORMATION', lang), s['section_header']))
    story.append(HRFlowable(width=page_w, color=BRAND_ACCENT, thickness=0.5, spaceAfter=PDF_HR_SPACE_AFTER))

    def _header(label):
        return Paragraph(_t(label, lang), s['label'])

    def _value(text):
        return Paragraph(_format_user_text_html(text or '—', lang), s['value'])

    headers = [
        _header('Name'),
        _header('Service Mode'),
    ]
    values = [
        _value(_customer_display_name(order.customer)),
        _value(_choice_display(order.service_mode, order.SERVICE_MODE_CHOICES, lang)),
    ]

    taken_by = _measurement_taken_by_name(order)
    if taken_by:
        headers.append(_header('Measured by'))
        values.append(_value(taken_by))

    if _is_rtl(lang):
        headers.reverse()
        values.reverse()

    data = [headers, values]
    n_cols = len(headers)
    col_w = page_w / n_cols
    style_cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), BRAND_LIGHT),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT' if _is_rtl(lang) else 'LEFT'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('BOX', (0, 0), (-1, -1), 0.4, BRAND_MID),
        ('LINEBELOW', (0, 0), (-1, 0), 0.5, BRAND_ACCENT),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, BRAND_MID),
    ]

    address = _order_delivery_address(order)
    if address:
        data.append([
            [
                Paragraph(_t('Address', lang), s['label']),
                Paragraph(_format_user_text_html(address, lang), s['value']),
            ]
        ] + [''] * (n_cols - 1))
        style_cmds.append(('SPAN', (0, 2), (-1, 2)))

    tbl = Table(data, colWidths=[col_w] * n_cols)
    tbl.setStyle(TableStyle(style_cmds))
    story.append(tbl)
    return story


def _build_riders_section(order, page_w, s, lang):
    """Measurement and delivery riders with contact numbers."""
    measurement_rider = getattr(order, 'measurement_rider', None)
    delivery_rider = getattr(order, 'delivery_rider', None)
    if not measurement_rider and not delivery_rider:
        return []

    story = []
    story.append(Paragraph(_t('RIDERS', lang), s['section_header']))
    story.append(HRFlowable(width=page_w, color=BRAND_ACCENT, thickness=0.5, spaceAfter=PDF_HR_SPACE_AFTER))

    col_w = page_w / 2
    headers = [
        Paragraph(_t('Measurement Rider', lang), s['label']),
        Paragraph(_t('Delivery Rider', lang), s['label']),
    ]
    cells = [
        _rider_info_cell(measurement_rider, lang, s),
        _rider_info_cell(delivery_rider, lang, s),
    ]
    if _is_rtl(lang):
        headers.reverse()
        cells.reverse()

    rider_tbl = Table([headers, cells], colWidths=[col_w, col_w])
    rider_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), BRAND_LIGHT),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('BOX', (0, 0), (-1, -1), 0.4, BRAND_MID),
        ('LINEBELOW', (0, 0), (-1, 0), 0.5, BRAND_ACCENT),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, BRAND_MID),
    ]))
    story.append(rider_tbl)
    return story


def _build_person_blocks(order, items, page_w, s, lang, measurement_fields):
    """Per-person item details with measurements and styles grouped together."""
    story = []
    blocks = []

    for item_index, item in enumerate(items, start=1):
        block = []
        block.append(_person_header_bar(item, order, page_w, s, lang, item_index))
        block.append(Spacer(1, PDF_ITEM_SPACER))
        block.append(_item_details_table(item, order, page_w, s, lang, item_index))
        block.append(Spacer(1, PDF_ITEM_SPACER))
        fabric_photos = _customer_fabric_images_table(item, page_w, s, lang)
        if fabric_photos:
            block.append(fabric_photos)
            block.append(Spacer(1, PDF_ITEM_SPACER))

        has_content = True
        meas = item.measurements if isinstance(item.measurements, dict) else {}
        meas_title = meas.get('title', '')
        grid = _measurements_grid_positioned(
            meas,
            measurement_fields,
            page_w,
            s,
            lang,
            title=meas_title,
        )
        if grid:
            block.append(grid)
            if meas:
                _append_measurement_notes(block, meas, page_w, s, lang)

        if item.custom_styles and isinstance(item.custom_styles, list):
            style_section = _custom_style_section(item.custom_styles, page_w, s, lang)
            if style_section:
                block.append(Paragraph(f'<b>{_safe_text(_t("Styles:", lang))}</b>', s['small']))
                block.append(Spacer(1, PDF_ITEM_SPACER))
                block.append(style_section)
                block.append(Spacer(1, PDF_ITEM_SPACER))

        if item.custom_instructions:
            _instr_label = _t('Instructions:', lang)
            block.append(Paragraph(
                f'<b>{_safe_text(_instr_label)}</b> {_format_user_text_html(item.custom_instructions, lang)}',
                s['small'],
            ))

        if has_content:
            blocks.append(block)

    if order.rider_measurements and isinstance(order.rider_measurements, dict) and order.rider_measurements:
        rider_meas = order.rider_measurements
        rider_grid = _measurements_grid_positioned(
            rider_meas,
            measurement_fields,
            page_w,
            s,
            lang,
        )
        if rider_grid:
            rider_block = [
                Paragraph(_t('RIDER MEASUREMENTS', lang), s['section_header']),
                HRFlowable(width=page_w, color=BRAND_ACCENT, thickness=0.5, spaceAfter=PDF_HR_SPACE_AFTER),
            ]
            if order.measurement_taken_at:
                rider_block.append(Paragraph(
                    f'<i>{_safe_text(_t("Measured at:", lang))} {_safe_text(_fmt_datetime(order.measurement_taken_at))}</i>',
                    s['small'],
                ))
                rider_block.append(Spacer(1, PDF_ITEM_SPACER))
            rider_block.append(rider_grid)
            _append_measurement_notes(rider_block, rider_meas, page_w, s, lang)
            blocks.append(rider_block)

    if not blocks:
        return story

    story.append(Paragraph(_t('ORDER ITEMS BY PERSON', lang), s['section_header']))
    story.append(HRFlowable(width=page_w, color=BRAND_ACCENT, thickness=0.5, spaceAfter=PDF_HR_SPACE_AFTER))
    for block_index, block in enumerate(blocks):
        if block_index > 0:
            story.append(Spacer(1, PDF_PERSON_BLOCK_SPACER))
        story.append(KeepTogether(block))
    story.append(Spacer(1, PDF_SECTION_SPACER))
    return story


def _build_priority_sections(order, items, page_w, s, lang, measurement_fields):
    """Backward-compatible alias for per-person blocks."""
    return _build_person_blocks(order, items, page_w, s, lang, measurement_fields)


def _order_info_rows(order, lang):
    """Key-value rows for order metadata."""
    order_type_display = _choice_display(order.order_type, order.ORDER_TYPE_CHOICES, lang)
    service_mode_display = _choice_display(order.service_mode, order.SERVICE_MODE_CHOICES, lang)
    rows = [
        ('Order Number', order.order_number, True),
        ('Order Type', order_type_display, True),
        ('Service Mode', service_mode_display, True),
        ('Items Count', str(order.items_count)),
    ]
    if order.estimated_delivery_date:
        rows.append(('Est. Delivery', _fmt_date(order.estimated_delivery_date)))
    if order.actual_delivery_date:
        rows.append(('Actual Delivery', _fmt_date(order.actual_delivery_date)))
    if order.appointment_date:
        appt = _fmt_date(order.appointment_date)
        if order.appointment_time:
            appt += f' at {order.appointment_time.strftime("%I:%M %p")}'
        rows.append(('Appointment', appt))
    if order.stitching_completion_date:
        rows.append(('Stitching Done', _fmt_date(order.stitching_completion_date)))
    return rows


def _tailor_info_rows(order):
    """Key-value rows for tailor and rider assignment."""
    tailor = order.tailor
    if not tailor:
        return []

    tailor_name = tailor.get_full_name() or tailor.username
    shop_name = '—'
    tailor_contact = getattr(tailor, 'phone', None) or '—'
    try:
        profile = tailor.tailor_profile
        shop_name = profile.shop_name or tailor_name
        tailor_contact = profile.contact_number or tailor_contact
    except Exception:
        pass

    rows = [
        ('Shop Name', shop_name, True),
        ('Tailor', tailor_name, True),
        ('Contact', tailor_contact, True),
    ]
    return rows


def _build_compact_info_section(order, page_w, s, lang):
    """Order summary and tailor shop details at the end of the PDF."""
    order_rows = _order_info_rows(order, lang)
    tailor_rows = _tailor_info_rows(order)
    if not order_rows and not tailor_rows:
        return []

    story = []
    story.append(Paragraph(_t('ORDER SUMMARY', lang), s['section_header']))
    story.append(HRFlowable(width=page_w, color=BRAND_ACCENT, thickness=0.5, spaceAfter=PDF_HR_SPACE_AFTER))

    gap = 2 * mm
    if tailor_rows:
        col_w = (page_w - gap) / 2
        left_tbl = _kv_table(order_rows, col_widths=[col_w * 0.38, col_w * 0.62], lang=lang)
        right_tbl = _kv_table(tailor_rows, col_widths=[col_w * 0.38, col_w * 0.62], lang=lang)
        outer = Table([[left_tbl, right_tbl]], colWidths=[col_w, col_w])
        outer.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(outer)
    else:
        story.append(_kv_table(order_rows, col_widths=[page_w * 0.30, page_w * 0.70], lang=lang))
    return story


def _build_header_section(order, page_w, s, lang):
    """Compact header banner and status strip."""
    is_rtl = _is_rtl(lang)
    story = []
    _receipt_label = _t('Order Receipt', lang) if is_rtl else 'Order Receipt'
    _font_bold = _AR_FONT_BOLD if (is_rtl and _ARABIC_FONT_AVAILABLE) else 'Helvetica-Bold'
    if is_rtl:
        header_data = [[
            Paragraph(
                f'<b>{_receipt_label}</b><br/><font color="#CCCCCC">{order.order_number}</font>',
                ParagraphStyle(f'hr_{lang}', parent=s['subtitle'], alignment=TA_RIGHT, fontSize=8,
                               textColor=WHITE, fontName=_font_bold, leading=10)
            ),
            Paragraph(_brand_title(lang), s['title']),
        ]]
    else:
        header_data = [[
            Paragraph('MGASK', s['title']),
            Paragraph(
                f'<b>Order Receipt</b><br/><font color="#CCCCCC">{order.order_number}</font>',
                ParagraphStyle(f'hr_{lang}', parent=s['subtitle'], alignment=TA_RIGHT, fontSize=8,
                               textColor=WHITE, fontName=_font_bold, leading=10)
            ),
        ]]
    header_tbl = Table(header_data, colWidths=[page_w * 0.5, page_w * 0.5])
    header_tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), BRAND_PRIMARY),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',    (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING',   (0, 0), (0, -1),  6),
        ('RIGHTPADDING',  (-1, 0), (-1, -1), 6),
        ('ROUNDEDCORNERS', [3, 3, 3, 3]),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, PDF_SECTION_SPACER))

    status_display = _choice_display(order.status, order.ORDER_STATUS_CHOICES, lang)
    tailor_status_display = (
        _choice_display(order.tailor_status, order.TAILOR_STATUS_CHOICES, lang)
        if order.tailor_status else _translate_label('N/A', lang)
    )
    status_color = _status_badge_color(order.status)
    _sb_font = _AR_FONT_BOLD if (is_rtl and _ARABIC_FONT_AVAILABLE) else 'Helvetica-Bold'
    _status_lbl = _t('Status:', lang)
    _tailor_lbl = _t('Tailor Status:', lang)
    _placed_lbl = _t('Placed:', lang)

    status_data = [[
        Paragraph(
            f'{_safe_text(_status_lbl)} <b>{_inline_value_html(status_display, lang)}</b>',
            ParagraphStyle(f'sb_{lang}', parent=s['value'], fontSize=7.5, textColor=WHITE, fontName=_sb_font,
                           alignment=TA_RIGHT if is_rtl else TA_LEFT),
        ),
        Paragraph(
            f'{_safe_text(_tailor_lbl)} <b>{_inline_value_html(tailor_status_display, lang)}</b>',
            ParagraphStyle(f'sb2_{lang}', parent=s['value'], fontSize=7.5, textColor=WHITE, fontName=_sb_font,
                           alignment=TA_CENTER),
        ),
        Paragraph(
            f'{_safe_text(_placed_lbl)} <b>{_safe_text(_fmt_datetime(order.created_at))}</b>',
            ParagraphStyle(f'sb3_{lang}', parent=s['value'], fontSize=7.5, textColor=WHITE, fontName=_sb_font,
                           alignment=TA_LEFT if is_rtl else TA_RIGHT),
        ),
    ]]
    if is_rtl:
        status_data[0].reverse()
    status_tbl = Table(status_data, colWidths=[page_w / 3] * 3)
    status_tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), status_color),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',    (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING',   (0, 0), (-1, -1), 4),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
    ]))
    story.append(status_tbl)
    story.append(Spacer(1, PDF_SECTION_SPACER))
    return story


def _build_items_summary_table(items, order, page_w, s, lang):
    """Slim items table: fabric, qty, ready — no nested measurements/styles."""
    is_rtl = _is_rtl(lang)
    story = []
    story.append(Paragraph(_t('ORDER ITEMS', lang), s['section_header']))
    story.append(HRFlowable(width=page_w, color=BRAND_ACCENT, thickness=0.5, spaceAfter=PDF_HR_SPACE_AFTER))

    if not items:
        story.append(Paragraph(_t('No items found for this order.', lang), s['value']))
        return story

    col_widths_items = [page_w * 0.65, page_w * 0.15, page_w * 0.20]
    item_headers = [
        Paragraph(_t('Item / Fabric', lang), s['table_header']),
        Paragraph(_t('Qty', lang), s['table_header']),
        Paragraph(_t('Ready', lang), s['table_header']),
    ]
    if is_rtl:
        item_headers.reverse()

    rows = [item_headers]
    _item_font_bold = _AR_FONT_BOLD if (is_rtl and _ARABIC_FONT_AVAILABLE) else 'Helvetica-Bold'

    for item_index, item in enumerate(items):
        fabric_cell = Paragraph(_item_fabric_label_html(item, order, lang), s['table_cell'])
        is_ready = ('✓ ' + _t('Yes', lang)) if item.is_ready else ('✗ ' + _t('No', lang))
        ready_color = colors.HexColor('#4CAF50') if item.is_ready else colors.HexColor('#F44336')
        row = [
            fabric_cell,
            Paragraph(_safe_text(str(item.quantity)), s['table_cell']),
            Paragraph(is_ready, ParagraphStyle(
                f'is_ready_{lang}_{item_index}', parent=s['table_cell'],
                textColor=ready_color, fontName=_item_font_bold,
            )),
        ]
        if is_rtl:
            row.reverse()
        rows.append(row)

    item_tbl = Table(rows, colWidths=col_widths_items, repeatRows=1)
    tbl_style = [
        ('BACKGROUND',    (0, 0), (-1, 0),  BRAND_PRIMARY),
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ('GRID',          (0, 0), (-1, -1), 0.3, BRAND_MID),
        ('LINEBELOW',     (0, 0), (-1, 0),  1,   BRAND_ACCENT),
        ('TOPPADDING',    (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, BRAND_LIGHT]),
    ]
    item_tbl.setStyle(TableStyle(tbl_style))
    story.append(item_tbl)
    return story


def _build_order_details_section(order, page_w, s, lang):
    """Order metadata KV table."""
    story = []
    story.append(Paragraph(_t('ORDER DETAILS', lang), s['section_header']))
    story.append(HRFlowable(width=page_w, color=BRAND_ACCENT, thickness=0.5, spaceAfter=PDF_HR_SPACE_AFTER))
    story.append(_kv_table(_order_info_rows(order, lang), col_widths=[page_w * 0.30, page_w * 0.70], lang=lang))
    return story


def _build_tailor_section(order, page_w, s, lang):
    """Tailor and rider assignment details."""
    story = []
    tailor_rows = _tailor_info_rows(order)
    if not tailor_rows:
        return story

    story.append(Paragraph(_t('TAILOR DETAILS', lang), s['section_header']))
    story.append(HRFlowable(width=page_w, color=BRAND_ACCENT, thickness=0.5, spaceAfter=PDF_HR_SPACE_AFTER))
    story.append(_kv_table(tailor_rows, lang=lang))
    return story


def _build_notes_section(order, page_w, s, lang):
    """Special instructions and internal notes."""
    story = []
    if not (order.special_instructions or order.notes):
        return story

    story.append(Paragraph(_t('NOTES & INSTRUCTIONS', lang), s['section_header']))
    story.append(HRFlowable(width=page_w, color=BRAND_ACCENT, thickness=0.5, spaceAfter=PDF_HR_SPACE_AFTER))
    if order.special_instructions:
        _si_label = _t('Special Instructions:', lang)
        story.append(Paragraph(
            f'<b>{_safe_text(_si_label)}</b> {_format_user_text_html(order.special_instructions, lang)}',
            s['small'],
        ))
        story.append(Spacer(1, PDF_ITEM_SPACER))
    if order.notes:
        _n_label = _t('Internal Notes:', lang)
        story.append(Paragraph(
            f'<b>{_safe_text(_n_label)}</b> {_format_user_text_html(order.notes, lang)}',
            s['small'],
        ))
    return story


def _build_status_history_section(order, page_w, s, lang):
    """Status change history table."""
    is_rtl = _is_rtl(lang)
    story = []
    history_qs = order.status_history.select_related('changed_by').order_by('-created_at')[:PDF_STATUS_HISTORY_MAX_ROWS]
    history = list(reversed(history_qs))
    if not history:
        return story

    story.append(Paragraph(_t('STATUS HISTORY', lang), s['section_header']))
    story.append(HRFlowable(width=page_w, color=BRAND_ACCENT, thickness=0.5, spaceAfter=PDF_HR_SPACE_AFTER))

    hist_headers = [
        Paragraph(_t('Date & Time', lang), s['table_header']),
        Paragraph(_t('Status', lang), s['table_header']),
        Paragraph(_t('Changed By', lang), s['table_header']),
        Paragraph(_t('Notes', lang), s['table_header']),
    ]
    if is_rtl:
        hist_headers.reverse()
    hist_rows = [hist_headers]

    for h in history:
        if h.changed_by and order.customer_id and h.changed_by_id == order.customer_id:
            changed_by = _translate_label('Customer', lang) if is_rtl else 'Customer'
        else:
            changed_by = h.changed_by.get_full_name() or h.changed_by.username if h.changed_by else '—'
        status_display = _choice_display(h.status, order.ORDER_STATUS_CHOICES, lang)
        note_text = _localized_note(h.notes, lang)
        hist_row = [
            Paragraph(_fmt_datetime(h.created_at), s['small']),
            Paragraph(_inline_value_html(status_display, lang), s['small']),
            Paragraph(_inline_value_html(changed_by, lang), s['small']),
            Paragraph(_format_user_text_html(note_text, lang), s['small']),
        ]
        if is_rtl:
            hist_row.reverse()
        hist_rows.append(hist_row)

    hist_tbl = Table(
        hist_rows,
        colWidths=[page_w * 0.25, page_w * 0.20, page_w * 0.22, page_w * 0.33],
        repeatRows=1,
    )
    hist_tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0),  BRAND_PRIMARY),
        ('TOPPADDING',    (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING',   (0, 0), (-1, -1), 4),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ('GRID',          (0, 0), (-1, -1), 0.3, BRAND_MID),
        ('LINEBELOW',     (0, 0), (-1, 0),  1,   BRAND_ACCENT),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, BRAND_LIGHT]),
    ]))
    story.append(hist_tbl)
    return story


def _build_comments_and_footer(order, page_w, s, lang):
    """Comments box and generated footer."""
    is_rtl = _is_rtl(lang)
    story = []
    story.append(Paragraph(_t('COMMENTS', lang), s['section_header']))
    story.append(HRFlowable(width=page_w, color=BRAND_ACCENT, thickness=0.5, spaceAfter=PDF_HR_SPACE_AFTER))
    comments_tbl = Table([['']], colWidths=[page_w], rowHeights=[PDF_COMMENT_BOX_HEIGHT])
    comments_tbl.setStyle(TableStyle([
        ('BOX',           (0, 0), (-1, -1), 0.7, BRAND_MID),
        ('BACKGROUND',    (0, 0), (-1, -1), WHITE),
        ('TOPPADDING',    (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING',   (0, 0), (-1, -1), 4),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
    ]))
    story.append(comments_tbl)
    story.append(Spacer(1, PDF_ITEM_SPACER))
    story.append(HRFlowable(width=page_w, color=BRAND_MID, thickness=0.5, spaceAfter=PDF_HR_SPACE_AFTER))
    generated_time = timezone.now().strftime('%d %b %Y, %I:%M %p')
    if is_rtl:
        _gen_label = _t('Generated by Mgask Platform', lang)
        _order_label = _t('Order', lang)
        footer_text = f'{_order_label} {order.order_number}  ·  {generated_time}  ·  {_gen_label}'
    else:
        footer_text = f'Generated by Mgask Platform  ·  {generated_time}  ·  Order {order.order_number}'
    story.append(Paragraph(footer_text, s['footer']))
    return story


def _pdf_top_margin():
    """Backward-compatible alias; prefer page-template specific top offsets."""
    return PDF_LATER_PAGE_TOP


def _canvas_prepare_text(text, lang):
    """Shape mixed RTL/LTR strings for raw canvas drawing."""
    if text is None:
        return ''
    logical = _normalize_rtl_text(text)
    if not logical:
        return ''
    if not _is_rtl(lang):
        return logical

    runs = _SCRIPT_RUN_RE.findall(logical)
    if not runs:
        return logical

    try:
        import arabic_reshaper
        from bidi.algorithm import get_display

        config = _get_reshaper_config()
        parts = []
        for run in runs:
            if _contains_arabic(run):
                if config:
                    parts.append(arabic_reshaper.reshape(run, configuration=config))
                else:
                    parts.append(arabic_reshaper.reshape(run))
            else:
                parts.append(run)
        return get_display(''.join(parts))
    except Exception:
        parts = []
        for run in runs:
            if _contains_arabic(run):
                parts.append(_shape_arabic(run))
            else:
                parts.append(run)
        return ''.join(parts)


def _canvas_fonts(lang):
    regular = _AR_FONT_REGULAR if (_is_rtl(lang) and _ARABIC_FONT_AVAILABLE) else 'Helvetica'
    bold = _AR_FONT_BOLD if (_is_rtl(lang) and _ARABIC_FONT_AVAILABLE) else 'Helvetica-Bold'
    return regular, bold


def _canvas_draw_line(canvas, x, y, text, lang, *, font_name, font_size, color, align='left'):
    canvas.setFont(font_name, font_size)
    canvas.setFillColor(color)
    display = _canvas_prepare_text(text, lang)
    if align == 'right':
        canvas.drawRightString(x, y, display)
    else:
        canvas.drawString(x, y, display)


class _OrderPDFPageContext:
    def __init__(self, order, lang):
        self.order = order
        self.lang = lang


def _canvas_page_label(lang, page_num):
    page_lbl = _translate_label('Page', lang)
    return f'{page_lbl} {page_num}'


def _canvas_draw_page_number(canvas, page_num, lang):
    _, font_bold = _canvas_fonts(lang)
    text = _canvas_page_label(lang, page_num)
    y = A4[1] - PDF_MARGIN_V
    right_x = A4[0] - PDF_MARGIN_H
    _canvas_draw_line(canvas, right_x, y, text, lang, font_name=font_bold, font_size=8, color=BRAND_SUBTEXT, align='right')


def _canvas_customer_summary_line(order, lang):
    customer_name = _customer_display_name(order.customer) or '—'
    return f'{order.order_number}  |  {customer_name}'


def _canvas_riders_summary_line(order, lang):
    meas_name, meas_phone = _rider_contact_details(getattr(order, 'measurement_rider', None))
    del_name, del_phone = _rider_contact_details(getattr(order, 'delivery_rider', None))
    meas_lbl = _translate_label('Measurement Rider', lang)
    del_lbl = _translate_label('Delivery Rider', lang)

    meas_text = f'{meas_lbl}: {meas_name or "—"}'
    if meas_phone:
        meas_text += f' ({meas_phone})'
    del_text = f'{del_lbl}: {del_name or "—"}'
    if del_phone:
        del_text += f' ({del_phone})'
    return f'{meas_text}  |  {del_text}'


def _canvas_draw_top_band(canvas, order, lang, *, include_riders):
    regular, bold = _canvas_fonts(lang)
    left_x = PDF_MARGIN_H
    right_x = A4[0] - PDF_MARGIN_H
    y_customer = A4[1] - PDF_MARGIN_V - PDF_PAGE_NUMBER_OFFSET - 1.5 * mm

    _canvas_draw_line(
        canvas, left_x, y_customer,
        _canvas_customer_summary_line(order, lang),
        lang, font_name=bold, font_size=7, color=BRAND_TEXT, align='left',
    )

    if include_riders:
        y_riders = y_customer - 4 * mm
        _canvas_draw_line(
            canvas, left_x, y_riders,
            _canvas_riders_summary_line(order, lang),
            lang, font_name=regular, font_size=6.5, color=BRAND_SUBTEXT, align='left',
        )
        canvas.setStrokeColor(BRAND_MID)
        canvas.setLineWidth(0.5)
        canvas.line(left_x, y_riders - 2 * mm, right_x, y_riders - 2 * mm)


def _make_pdf_page_callbacks(ctx):
    def _draw_first_page(canvas, doc):
        canvas.saveState()
        _canvas_draw_page_number(canvas, canvas.getPageNumber(), ctx.lang)
        _canvas_draw_top_band(canvas, ctx.order, ctx.lang, include_riders=False)
        canvas.restoreState()

    def _draw_later_page(canvas, doc):
        canvas.saveState()
        _canvas_draw_page_number(canvas, canvas.getPageNumber(), ctx.lang)
        _canvas_draw_top_band(canvas, ctx.order, ctx.lang, include_riders=True)
        canvas.restoreState()

    return _draw_first_page, _draw_later_page


class _OrderPDFDoc(BaseDocTemplate):
    """PDF doc with a taller top band on continuation pages for repeat headers."""


def _build_order_pdf_doc(buffer):
    doc = _OrderPDFDoc(
        buffer,
        pagesize=A4,
        leftMargin=PDF_MARGIN_H,
        rightMargin=PDF_MARGIN_H,
        bottomMargin=PDF_MARGIN_V,
        topMargin=PDF_FIRST_PAGE_TOP,
        title='Order PDF',
        author='Mgask Platform',
    )
    first_frame = Frame(
        doc.leftMargin,
        doc.bottomMargin,
        doc.width,
        A4[1] - doc.bottomMargin - PDF_FIRST_PAGE_TOP,
        id='first',
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
    )
    later_frame = Frame(
        doc.leftMargin,
        doc.bottomMargin,
        doc.width,
        A4[1] - doc.bottomMargin - PDF_LATER_PAGE_TOP,
        id='later',
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
    )
    return doc, first_frame, later_frame


def generate_order_pdf_reportlab(order, lang='en') -> bytes:
    """Legacy ReportLab renderer for the complete order PDF."""
    buffer = io.BytesIO()
    page_ctx = _OrderPDFPageContext(order, lang)
    draw_first_page, draw_later_page = _make_pdf_page_callbacks(page_ctx)
    doc, first_frame, later_frame = _build_order_pdf_doc(buffer)
    doc.addPageTemplates([
        PageTemplate(id='First', frames=[first_frame], onPage=draw_first_page),
        PageTemplate(id='Later', frames=[later_frame], onPage=draw_later_page),
    ])
    doc.title = f'Order {order.order_number}'

    s = _styles(lang)
    page_w = _pdf_page_width()
    measurement_fields = _measurement_field_map()
    items = list(
        order.order_items.select_related('fabric', 'family_member')
        .prefetch_related('customer_fabric_images')
        .all()
    )

    story = [NextPageTemplate('Later')]
    story.extend(_build_header_section(order, page_w, s, lang))
    story.extend(_build_customer_section(order, page_w, s, lang))
    story.append(Spacer(1, PDF_SECTION_SPACER))
    riders = _build_riders_section(order, page_w, s, lang)
    if riders:
        story.extend(riders)
        story.append(Spacer(1, PDF_SECTION_SPACER))
    story.extend(_build_person_blocks(order, items, page_w, s, lang, measurement_fields))
    story.extend(_build_compact_info_section(order, page_w, s, lang))
    notes = _build_notes_section(order, page_w, s, lang)
    if notes:
        story.append(Spacer(1, PDF_SECTION_SPACER))
        story.extend(notes)
    history = _build_status_history_section(order, page_w, s, lang)
    if history:
        story.append(Spacer(1, PDF_SECTION_SPACER))
        story.extend(history)
    story.append(Spacer(1, PDF_SECTION_SPACER))
    story.extend(_build_comments_and_footer(order, page_w, s, lang))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def generate_order_pdf(order, lang='en') -> bytes:
    """Generate the complete order PDF via the document engine."""
    from apps.documents.service import generate_order_document

    return generate_order_document(order, lang=lang)
