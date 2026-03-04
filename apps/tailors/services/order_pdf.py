# apps/tailors/services/order_pdf.py
"""
PDF generation service for tailor order download.
Uses reportlab (already in requirements.txt).
"""
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from django.utils import timezone


# ─── Brand colors ────────────────────────────────────────────────────────────
BRAND_PRIMARY   = colors.HexColor('#1A1A2E')   # Dark navy
BRAND_ACCENT    = colors.HexColor('#C9A84C')   # Gold
BRAND_LIGHT     = colors.HexColor('#F5F5F5')   # Light grey
BRAND_MID       = colors.HexColor('#DDDDDD')   # Divider grey
BRAND_TEXT      = colors.HexColor('#333333')   # Main text
BRAND_SUBTEXT   = colors.HexColor('#666666')   # Secondary text
WHITE           = colors.white


def _styles():
    """Return a dict of named ParagraphStyles."""
    base = getSampleStyleSheet()

    return {
        'title': ParagraphStyle(
            'Title',
            parent=base['Normal'],
            fontSize=22,
            fontName='Helvetica-Bold',
            textColor=WHITE,
            alignment=TA_LEFT,
            spaceAfter=2,
        ),
        'subtitle': ParagraphStyle(
            'Subtitle',
            parent=base['Normal'],
            fontSize=10,
            fontName='Helvetica',
            textColor=colors.HexColor('#CCCCCC'),
            alignment=TA_LEFT,
        ),
        'section_header': ParagraphStyle(
            'SectionHeader',
            parent=base['Normal'],
            fontSize=9,
            fontName='Helvetica-Bold',
            textColor=BRAND_ACCENT,
            spaceBefore=6,
            spaceAfter=3,
        ),
        'label': ParagraphStyle(
            'Label',
            parent=base['Normal'],
            fontSize=8,
            fontName='Helvetica-Bold',
            textColor=BRAND_SUBTEXT,
        ),
        'value': ParagraphStyle(
            'Value',
            parent=base['Normal'],
            fontSize=9,
            fontName='Helvetica',
            textColor=BRAND_TEXT,
        ),
        'small': ParagraphStyle(
            'Small',
            parent=base['Normal'],
            fontSize=7.5,
            fontName='Helvetica',
            textColor=BRAND_SUBTEXT,
        ),
        'footer': ParagraphStyle(
            'Footer',
            parent=base['Normal'],
            fontSize=7,
            fontName='Helvetica',
            textColor=BRAND_SUBTEXT,
            alignment=TA_CENTER,
        ),
        'table_header': ParagraphStyle(
            'TableHeader',
            parent=base['Normal'],
            fontSize=8,
            fontName='Helvetica-Bold',
            textColor=WHITE,
        ),
        'table_cell': ParagraphStyle(
            'TableCell',
            parent=base['Normal'],
            fontSize=8,
            fontName='Helvetica',
            textColor=BRAND_TEXT,
        ),
        'total_label': ParagraphStyle(
            'TotalLabel',
            parent=base['Normal'],
            fontSize=9,
            fontName='Helvetica-Bold',
            textColor=BRAND_TEXT,
            alignment=TA_RIGHT,
        ),
        'total_value': ParagraphStyle(
            'TotalValue',
            parent=base['Normal'],
            fontSize=10,
            fontName='Helvetica-Bold',
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


def _kv_table(rows, col_widths=None):
    """
    Build a compact key-value table.
    rows = list of (label_str, value_str) tuples.
    """
    s = _styles()
    page_w = A4[0] - 40 * mm
    col_widths = col_widths or [page_w * 0.35, page_w * 0.65]

    data = [
        [Paragraph(lbl, s['label']), Paragraph(str(val) if val else '—', s['value'])]
        for lbl, val in rows
    ]
    tbl = Table(data, colWidths=col_widths, hAlign='LEFT')
    tbl.setStyle(TableStyle([
        ('VALIGN',     (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    return tbl


def generate_order_pdf(order) -> bytes:
    """
    Generate a professional PDF for a single order.

    Args:
        order: apps.orders.models.Order instance (with related objects pre-fetched or lazy).

    Returns:
        bytes: Raw PDF file content.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title=f'Order {order.order_number}',
        author='Zthob Platform',
    )

    s = _styles()
    page_w = A4[0] - 40 * mm
    story = []

    # ── Header banner ─────────────────────────────────────────────────────────
    header_data = [[
        Paragraph('ZTHOB', s['title']),
        Paragraph(
            f'<b>Order Receipt</b><br/><font color="#CCCCCC">{order.order_number}</font>',
            ParagraphStyle('hr', parent=s['subtitle'], alignment=TA_RIGHT, fontSize=10,
                           textColor=WHITE, fontName='Helvetica-Bold')
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
    status_display  = order.get_status_display()
    tailor_status_display = order.get_tailor_status_display() if order.tailor_status else 'N/A'
    status_color = _status_badge_color(order.status)

    status_data = [[
        Paragraph(f'Status: <b>{status_display}</b>', ParagraphStyle(
            'sb', parent=s['value'], fontSize=9, textColor=WHITE, fontName='Helvetica-Bold'
        )),
        Paragraph(f'Tailor Status: <b>{tailor_status_display}</b>', ParagraphStyle(
            'sb2', parent=s['value'], fontSize=9, textColor=WHITE, fontName='Helvetica-Bold',
            alignment=TA_CENTER
        )),
        Paragraph(f'Placed: <b>{_fmt_datetime(order.created_at)}</b>', ParagraphStyle(
            'sb3', parent=s['value'], fontSize=9, textColor=WHITE, fontName='Helvetica-Bold',
            alignment=TA_RIGHT
        )),
    ]]
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

    # ── Two-column: Order Info + Customer Info ────────────────────────────────
    # Order Info
    order_type_display = order.get_order_type_display()
    service_mode_display = order.get_service_mode_display()
    payment_status_display = order.get_payment_status_display()
    payment_method_display = order.get_payment_method_display()

    order_info_rows = [
        ('Order Number',     order.order_number),
        ('Order Type',       order_type_display),
        ('Service Mode',     service_mode_display),
        ('Payment Method',   payment_method_display),
        ('Payment Status',   payment_status_display),
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

    # Customer Info
    customer = order.customer
    customer_name = customer.get_full_name() or customer.username if customer else '—'
    customer_phone = getattr(customer, 'phone', None) or '—'
    customer_email = getattr(customer, 'email', '') or '—'

    # Delivery address
    addr_text = '—'
    if order.delivery_formatted_address:
        addr_text = order.delivery_formatted_address
    elif order.delivery_address:
        a = order.delivery_address
        parts = filter(None, [a.street, a.city, a.country])
        addr_text = ', '.join(parts)
    elif order.delivery_street:
        parts = filter(None, [order.delivery_street, order.delivery_city])
        addr_text = ', '.join(parts)

    customer_rows = [
        ('Customer Name',  customer_name),
        ('Phone',          customer_phone),
        ('Email',          customer_email),
        ('Delivery Addr.', addr_text),
    ]
    if order.delivery_extra_info:
        customer_rows.append(('Extra Info', order.delivery_extra_info))

    # Family member
    if order.family_member:
        fm = order.family_member
        customer_rows.append(('For (Family)', fm.name))
        if fm.relationship:
            customer_rows.append(('Relationship', fm.relationship))

    col_half = page_w / 2 - 3 * mm

    def _section_block(title_str, kv_rows, col_w):
        inner = []
        inner.append(Paragraph(title_str, s['section_header']))
        inner.append(HRFlowable(width=col_w, color=BRAND_ACCENT, thickness=0.5, spaceAfter=4))
        inner.append(_kv_table(kv_rows, col_widths=[col_w * 0.42, col_w * 0.58]))
        return inner

    # Combine in 2-col table
    left_cell  = _section_block('ORDER DETAILS', order_info_rows, col_half)
    right_cell = _section_block('CUSTOMER DETAILS', customer_rows, col_half)

    two_col = Table([[left_cell, right_cell]], colWidths=[col_half, col_half + 6 * mm])
    two_col.setStyle(TableStyle([
        ('VALIGN',       (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING',  (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING',   (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 0),
        ('LINEAFTER',    (0, 0), (0, -1),  0.5, BRAND_MID),
        ('RIGHTPADDING', (0, 0), (0, -1),  6),
        ('LEFTPADDING',  (1, 0), (1, -1),  6),
    ]))
    story.append(two_col)
    story.append(Spacer(1, 5 * mm))

    # ── Tailor Info ───────────────────────────────────────────────────────────
    tailor = order.tailor
    if tailor:
        story.append(Paragraph('TAILOR DETAILS', s['section_header']))
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
            ('Contact',    tailor_contact),
        ]
        if order.assigned_rider:
            rider = order.assigned_rider
            tailor_rows.append(('Assigned Rider', rider.get_full_name() or rider.username))

        story.append(_kv_table(tailor_rows))
        story.append(Spacer(1, 4 * mm))

    # ── Special instructions / notes ──────────────────────────────────────────
    if order.special_instructions or order.notes:
        story.append(Paragraph('NOTES & INSTRUCTIONS', s['section_header']))
        story.append(HRFlowable(width=page_w, color=BRAND_ACCENT, thickness=0.5, spaceAfter=4))
        if order.special_instructions:
            story.append(Paragraph(f'<b>Special Instructions:</b> {order.special_instructions}', s['value']))
            story.append(Spacer(1, 2 * mm))
        if order.notes:
            story.append(Paragraph(f'<b>Internal Notes:</b> {order.notes}', s['value']))
        story.append(Spacer(1, 4 * mm))

    # ── Order Items table ─────────────────────────────────────────────────────
    story.append(Paragraph('ORDER ITEMS', s['section_header']))
    story.append(HRFlowable(width=page_w, color=BRAND_ACCENT, thickness=0.5, spaceAfter=4))

    items = list(order.order_items.select_related('fabric', 'family_member').all())

    if items:
        col_widths_items = [
            page_w * 0.28,  # Item / Fabric
            page_w * 0.18,  # For (recipient)
            page_w * 0.08,  # Qty
            page_w * 0.15,  # Unit Price
            page_w * 0.15,  # Total Price
            page_w * 0.16,  # Status
        ]

        item_headers = [
            Paragraph('Item / Fabric', s['table_header']),
            Paragraph('For', s['table_header']),
            Paragraph('Qty', s['table_header']),
            Paragraph('Unit Price', s['table_header']),
            Paragraph('Total Price', s['table_header']),
            Paragraph('Ready', s['table_header']),
        ]
        item_rows = [item_headers]

        for item in items:
            fabric_name = item.fabric.name if item.fabric else 'Measurement Service'
            fabric_sku  = f'SKU: {item.fabric.sku}' if item.fabric and item.fabric.sku else ''
            fabric_cell = Paragraph(
                f'{fabric_name}<br/><font color="#888888" size="7">{fabric_sku}</font>',
                s['table_cell']
            )

            recipient = '—'
            if item.family_member:
                recipient = item.family_member.name
            elif customer:
                recipient = customer_name

            is_ready = '✓ Yes' if item.is_ready else '✗ No'
            ready_color = colors.HexColor('#4CAF50') if item.is_ready else colors.HexColor('#F44336')

            item_rows.append([
                fabric_cell,
                Paragraph(recipient, s['table_cell']),
                Paragraph(str(item.quantity), s['table_cell']),
                Paragraph(_fmt_amount(item.unit_price), s['table_cell']),
                Paragraph(_fmt_amount(item.total_price), s['table_cell']),
                Paragraph(is_ready, ParagraphStyle(
                    'is_ready', parent=s['table_cell'],
                    textColor=ready_color, fontName='Helvetica-Bold'
                )),
            ])

            # Custom instructions row
            if item.custom_instructions:
                item_rows.append([
                    Paragraph(
                        f'<i>Instructions: {item.custom_instructions}</i>',
                        s['small']
                    ),
                    '', '', '', '', ''
                ])

            # Measurements row
            if item.measurements:
                meas = item.measurements
                if isinstance(meas, dict):
                    meas_pairs = [f'{k}: {v}' for k, v in meas.items() if k != 'title']
                    meas_text = '  |  '.join(meas_pairs[:8])  # cap to avoid overflow
                    if len(meas_pairs) > 8:
                        meas_text += f'  ... (+{len(meas_pairs) - 8} more)'
                    if meas_text:
                        item_rows.append([
                            Paragraph(
                                f'<i>Measurements: {meas_text}</i>',
                                s['small']
                            ),
                            '', '', '', '', ''
                        ])

            # Custom styles row
            if item.custom_styles and isinstance(item.custom_styles, list):
                style_texts = [
                    f'{cs.get("style_type", "").replace("_", " ").title()}: {cs.get("label", "")}'
                    for cs in item.custom_styles if cs.get('label')
                ]
                if style_texts:
                    item_rows.append([
                        Paragraph(
                            f'<i>Styles: {",  ".join(style_texts)}</i>',
                            s['small']
                        ),
                        '', '', '', '', ''
                    ])

        items_tbl = Table(item_rows, colWidths=col_widths_items, repeatRows=1)
        items_tbl.setStyle(TableStyle([
            # Header row style
            ('BACKGROUND',    (0, 0), (-1, 0),  BRAND_PRIMARY),
            ('TOPPADDING',    (0, 0), (-1, 0),  6),
            ('BOTTOMPADDING', (0, 0), (-1, 0),  6),
            ('LEFTPADDING',   (0, 0), (-1, 0),  6),
            ('RIGHTPADDING',  (0, 0), (-1, 0),  6),
            # Body rows
            ('BACKGROUND',    (0, 1), (-1, -1), WHITE),
            ('ROWBACKGROUNDS',(0, 1), (-1, -1), [WHITE, BRAND_LIGHT]),
            ('TOPPADDING',    (0, 1), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            ('LEFTPADDING',   (0, 1), (-1, -1), 6),
            ('RIGHTPADDING',  (0, 1), (-1, -1), 6),
            ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
            ('GRID',          (0, 0), (-1, -1), 0.3, BRAND_MID),
            ('LINEBELOW',     (0, 0), (-1, 0),  1,   BRAND_ACCENT),
        ]))
        story.append(items_tbl)
    else:
        story.append(Paragraph('No items found for this order.', s['value']))

    story.append(Spacer(1, 6 * mm))

    # ── Order-level measurements (rider measurements) ─────────────────────────
    if order.rider_measurements and isinstance(order.rider_measurements, dict) and order.rider_measurements:
        story.append(Paragraph('RIDER MEASUREMENTS', s['section_header']))
        story.append(HRFlowable(width=page_w, color=BRAND_ACCENT, thickness=0.5, spaceAfter=4))
        meas_pairs = [
            (str(k).replace('_', ' ').title(), str(v))
            for k, v in order.rider_measurements.items()
        ]
        # Render in 2-column layout
        half = len(meas_pairs) // 2 + len(meas_pairs) % 2
        left_meas  = meas_pairs[:half]
        right_meas = meas_pairs[half:]

        def _meas_col(rows, w):
            data = [
                [Paragraph(l, s['label']), Paragraph(v, s['value'])]
                for l, v in rows
            ]
            if not data:
                return Paragraph('', s['value'])
            t = Table(data, colWidths=[w * 0.5, w * 0.5], hAlign='LEFT')
            t.setStyle(TableStyle([
                ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING',    (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                ('LEFTPADDING',   (0, 0), (-1, -1), 0),
                ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
            ]))
            return t

        meas_col_w = page_w / 2
        meas_layout = Table(
            [[_meas_col(left_meas, meas_col_w), _meas_col(right_meas, meas_col_w)]],
            colWidths=[meas_col_w, meas_col_w]
        )
        meas_layout.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING',  (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING',   (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING',(0, 0), (-1, -1), 0),
        ]))
        story.append(meas_layout)
        story.append(Spacer(1, 5 * mm))

    # ── Pricing Summary ───────────────────────────────────────────────────────
    story.append(Paragraph('PRICING SUMMARY', s['section_header']))
    story.append(HRFlowable(width=page_w, color=BRAND_ACCENT, thickness=0.5, spaceAfter=4))

    price_rows = []

    def _price_row(label, amount, bold=False, accent=False):
        lbl_style = ParagraphStyle('pl', parent=s['label'], alignment=TA_RIGHT,
                                    fontName='Helvetica-Bold' if bold else 'Helvetica')
        val_style = ParagraphStyle('pv', parent=s['value'], alignment=TA_RIGHT,
                                    fontSize=10 if bold else 9,
                                    textColor=BRAND_ACCENT if accent else BRAND_TEXT,
                                    fontName='Helvetica-Bold' if bold else 'Helvetica')
        return [Paragraph('', s['label']), Paragraph(label, lbl_style),
                Paragraph(_fmt_amount(amount), val_style)]

    price_rows.append(_price_row('Subtotal', order.subtotal))
    if order.stitching_price:
        price_rows.append(_price_row('Stitching Price', order.stitching_price))
    if order.tax_amount:
        price_rows.append(_price_row('Tax', order.tax_amount))
    if order.delivery_fee:
        price_rows.append(_price_row('Delivery Fee', order.delivery_fee))
    if order.system_fee:
        price_rows.append(_price_row('Platform Fee', order.system_fee))

    # Divider row
    price_rows.append([
        Paragraph('', s['label']),
        HRFlowable(width=page_w * 0.35, color=BRAND_MID, thickness=0.5),
        HRFlowable(width=page_w * 0.25, color=BRAND_MID, thickness=0.5),
    ])
    price_rows.append(_price_row('TOTAL AMOUNT', order.total_amount, bold=True, accent=True))

    pricing_tbl = Table(
        price_rows,
        colWidths=[page_w * 0.40, page_w * 0.35, page_w * 0.25],
        hAlign='RIGHT'
    )
    pricing_tbl.setStyle(TableStyle([
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',    (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING',   (0, 0), (-1, -1), 0),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
        ('BACKGROUND',    (0, -1), (-1, -1), BRAND_LIGHT),
    ]))
    story.append(pricing_tbl)
    story.append(Spacer(1, 6 * mm))

    # ── Status History ────────────────────────────────────────────────────────
    history_qs = order.status_history.select_related('changed_by').order_by('created_at')[:20]
    history = list(history_qs)

    if history:
        story.append(Paragraph('STATUS HISTORY', s['section_header']))
        story.append(HRFlowable(width=page_w, color=BRAND_ACCENT, thickness=0.5, spaceAfter=4))

        hist_headers = [
            Paragraph('Date & Time', s['table_header']),
            Paragraph('Status', s['table_header']),
            Paragraph('Changed By', s['table_header']),
            Paragraph('Notes', s['table_header']),
        ]
        hist_rows = [hist_headers]

        for h in history:
            changed_by = h.changed_by.get_full_name() or h.changed_by.username if h.changed_by else '—'
            hist_rows.append([
                Paragraph(_fmt_datetime(h.created_at), s['small']),
                Paragraph(h.get_status_display(), s['small']),
                Paragraph(changed_by, s['small']),
                Paragraph(h.notes or '—', s['small']),
            ])

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

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(HRFlowable(width=page_w, color=BRAND_MID, thickness=0.5, spaceAfter=4))
    generated_time = timezone.now().strftime('%d %b %Y, %I:%M %p')
    story.append(Paragraph(
        f'Generated by Zthob Platform  ·  {generated_time}  ·  Order {order.order_number}',
        s['footer']
    ))

    # Build PDF
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
