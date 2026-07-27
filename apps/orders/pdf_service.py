"""
Work Order PDF Generation Service

Generates printable PDF work orders for tailors with complete order specifications
including measurements, fabric details, customization with images, and customer notes.

Supports both Arabic and English with proper RTL text handling.
"""
import os
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from arabic_reshaper import reshape
from bidi.algorithm import get_display
from PIL import Image as PILImage
from django.conf import settings
from zthob.languages import is_rtl_language


_WORK_ORDER_UR = {
    'Work Order': 'کام کا آرڈر',
    'Customer Information': 'گاہک کی معلومات',
    'Customer:': ':گاہک',
    'Phone:': ':فون',
    'Service:': ':سروس',
    'Home Delivery': 'گھر پر ڈیلیوری',
    'Walk-in': 'دکان پر آنا',
    'Measurements': 'ناپ',
    'Fabric Details': 'کپڑے کی تفصیلات',
    'Fabric:': ':کپڑا',
    'Color:': ':رنگ',
    'Customization': 'حسب ضرورت',
    'Special Instructions': 'خصوصی ہدایات',
    'Collar Style': 'کالر کا انداز',
    'Cuff Style': 'آستین کا انداز',
    'Pocket Style': 'جیب کا انداز',
    'Neck': 'گردن',
    'Shoulder': 'کندھا',
    'Chest': 'سینہ',
    'Waist': 'کمر',
    'Hip': 'کولہا',
    'Sleeve Length': 'آستین کی لمبائی',
    'Arm Hole': 'بازو کا سوراخ',
    'Body Length': 'جسم کی لمبائی',
    'Thobe Length': 'قمیض کی لمبائی',
}


class WorkOrderPDFService:
    """Service for generating work order PDFs"""
    
    # Page dimensions
    PAGE_WIDTH, PAGE_HEIGHT = A4
    MARGIN = 20 * mm
    
    def __init__(self, order, language='ar'):
        """
        Initialize PDF service
        
        Args:
            order: Order instance
            language: 'ar' for Arabic, 'en' for English, 'ur' for Urdu
        """
        self.order = order
        self.language = language
        self.buffer = BytesIO()
        self.pdf = canvas.Canvas(self.buffer, pagesize=A4)
        self.y_position = self.PAGE_HEIGHT - self.MARGIN

    def _is_rtl(self):
        return is_rtl_language(self.language)

    def _label(self, en_text, ar_text, ur_key=None):
        if self.language == 'en':
            return en_text
        if self.language == 'ur':
            return _WORK_ORDER_UR.get(ur_key or en_text, ar_text)
        return ar_text
        
    def render_text(self, text, is_arabic=None):
        """
        Render text with proper Arabic/Urdu RTL handling
        
        Args:
            text: Text to render
            is_arabic: Force RTL rendering, auto-detect if None
        """
        if is_arabic is None:
            is_arabic = self._is_rtl()
        
        if is_arabic and text:
            reshaped = reshape(str(text))
            return get_display(reshaped)
        return str(text)
    
    def draw_header(self):
        """Draw PDF header with order info"""
        # Title
        self.pdf.setFont("Helvetica-Bold", 18)
        title = self._label("Work Order", "أمر العمل")
        title_rendered = self.render_text(title)
        self.pdf.drawCenteredString(self.PAGE_WIDTH / 2, self.y_position, title_rendered)
        self.y_position -= 10 * mm
        
        # Order number
        self.pdf.setFont("Helvetica-Bold", 14)
        if self._is_rtl():
            order_num = f"#{self.order.order_number} الطلب رقم"
            if self.language == 'ur':
                order_num = f"#{self.order.order_number} آرڈر نمبر"
        else:
            order_num = f"Order #{self.order.order_number}"
        order_num_rendered = self.render_text(order_num)
        self.pdf.drawCenteredString(self.PAGE_WIDTH / 2, self.y_position, order_num_rendered)
        self.y_position -= 15 * mm
        
        # Horizontal line
        self.pdf.line(self.MARGIN, self.y_position, self.PAGE_WIDTH - self.MARGIN, self.y_position)
        self.y_position -= 5 * mm
        
    def draw_customer_info(self):
        """Draw customer information section"""
        self.pdf.setFont("Helvetica-Bold", 12)
        section_title = self._label("Customer Information", "معلومات العميل")
        self.pdf.drawString(self.MARGIN, self.y_position, self.render_text(section_title))
        self.y_position -= 7 * mm
        
        self.pdf.setFont("Helvetica", 10)
        
        # Customer name
        customer_name = self.order.customer.username if self.order.customer else "N/A"
        name_label = self._label("Customer:", ":العميل")
        self.pdf.drawString(self.MARGIN, self.y_position, 
                          self.render_text(f"{name_label} {customer_name}"))
        self.y_position -= 5 * mm
        
        # Phone
        phone = self.order.customer.phone_number if self.order.customer else "N/A"
        phone_label = self._label("Phone:", ":الهاتف")
        self.pdf.drawString(self.MARGIN, self.y_position,
                          self.render_text(f"{phone_label} {phone}"))
        self.y_position -= 5 * mm
        
        # Service mode
        service_label = self._label("Service:", ":الخدمة")
        service_val = "Home Delivery" if self.order.service_mode == 'home_delivery' else "Walk-in"
        if self._is_rtl():
            service_val = self._label(
                "Home Delivery" if self.order.service_mode == 'home_delivery' else "Walk-in",
                "توصيل منزلي" if self.order.service_mode == 'home_delivery' else "استلام من المحل",
            )
        self.pdf.drawString(self.MARGIN, self.y_position,
                          self.render_text(f"{service_label} {service_val}"))
        self.y_position -= 10 * mm
        
    def draw_measurements(self, order_item):
        """Draw measurements table for an order item"""
        if not order_item.measurements:
            return
        
        self.pdf.setFont("Helvetica-Bold", 12)
        title = self._label("Measurements", "القياسات")
        self.pdf.drawString(self.MARGIN, self.y_position, self.render_text(title))
        self.y_position -= 7 * mm
        
        # Build measurements table data
        table_data = []
        measurements = order_item.measurements
        
        # Measurement labels
        meas_labels = {
            'neck': ('Neck', 'الرقبة', 'گردن'),
            'shoulder': ('Shoulder', 'الكتف', 'کندھا'),
            'chest': ('Chest', 'الصدر', 'سینہ'),
            'waist': ('Waist', 'الخصر', 'کمر'),
            'hip': ('Hip', 'الورك', 'کولہا'),
            'sleeve_length': ('Sleeve Length', 'طول الكم', 'آستین کی لمبائی'),
            'arm_hole': ('Arm Hole', 'فتحة الذراع', 'بازو کا سوراخ'),
            'body_length': ('Body Length', 'طول الجسم', 'جسم کی لمبائی'),
            'thobe_length': ('Thobe Length', 'طول الثوب', 'قمیض کی لمبائی'),
        }
        
        row = []
        for key, (en_label, ar_label, ur_label) in meas_labels.items():
            if key in measurements and measurements[key]:
                if self.language == 'en':
                    label = en_label
                elif self.language == 'ur':
                    label = ur_label
                else:
                    label = ar_label
                value = f"{measurements[key]} cm"
                row.append(f"{self.render_text(label)}: {value}")
                
                if len(row) == 2:  # Two columns per row
                    table_data.append(row)
                    row = []
        
        if row:  # Add remaining items
            table_data.append(row)
        
        if table_data:
            # Create table
            col_width = (self.PAGE_WIDTH - 2 * self.MARGIN) / 2
            table = Table(table_data, colWidths=[col_width, col_width])
            table.setStyle(TableStyle([
                ('FONT', (0, 0), (-1, -1), 'Helvetica', 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('PADDING', (0, 0), (-1, -1), 3),
            ]))
            
            # Draw table
            table_height = table.wrap(0, 0)[1]
            if self.y_position - table_height < self.MARGIN:
                self.pdf.showPage()
                self.y_position = self.PAGE_HEIGHT - self.MARGIN
            
            table.drawOn(self.pdf, self.MARGIN, self.y_position - table_height)
            self.y_position -= table_height + 5 * mm
    
    def draw_fabric_info(self, order_item):
        """Draw fabric information"""
        if not order_item.fabric:
            return
        
        self.pdf.setFont("Helvetica-Bold", 12)
        title = self._label("Fabric Details", "تفاصيل القماش")
        self.pdf.drawString(self.MARGIN, self.y_position, self.render_text(title))
        self.y_position -= 7 * mm
        
        self.pdf.setFont("Helvetica", 10)
        fabric = order_item.fabric
        
        # Fabric name
        fabric_label = self._label("Fabric:", ":القماش")
        self.pdf.drawString(self.MARGIN, self.y_position,
                          self.render_text(f"{fabric_label} {fabric.name}"))
        self.y_position -= 5 * mm
        
        # Color
        color_label = self._label("Color:", ":اللون")
        self.pdf.drawString(self.MARGIN, self.y_position,
                          self.render_text(f"{color_label} {fabric.color}"))
        self.y_position -= 10 * mm
    
    def draw_customizations(self, order_item):
        """Draw customization details with images"""
        if not hasattr(order_item, 'customization') or not order_item.customization:
            return
        
        self.pdf.setFont("Helvetica-Bold", 12)
        title = self._label("Customization", "التخصيص")
        self.pdf.drawString(self.MARGIN, self.y_position, self.render_text(title))
        self.y_position -= 7 * mm
        
        self.pdf.setFont("Helvetica", 10)
        customization = order_item.customization
        
        # Helper to draw customization with optional image
        def draw_custom_item(label_en, label_ar, value, image_path=None, label_ur=None):
            label = self._label(label_en, label_ar, ur_key=label_ur or label_en)
            self.pdf.drawString(self.MARGIN, self.y_position,
                              self.render_text(f"{label}: {value}"))
            self.y_position -= 5 * mm
            
            # Draw image if available
            if image_path and os.path.exists(image_path):
                try:
                    img_width = 30 * mm
                    img_height = 30 * mm
                    if self.y_position - img_height < self.MARGIN:
                        self.pdf.showPage()
                        self.y_position = self.PAGE_HEIGHT - self.MARGIN
                    
                    self.pdf.drawImage(image_path, self.MARGIN + 5 * mm,
                                     self.y_position - img_height,
                                     width=img_width, height=img_height,
                                     preserveAspectRatio=True)
                    self.y_position -= img_height + 3 * mm
                except Exception as e:
                    pass  # Skip if image fails to load
        
        # Draw each customization type
        if customization.collar_style:
            draw_custom_item("Collar Style", "نمط الياقة",
                           customization.collar_style.value,
                           customization.collar_style.asset_path,
                           label_ur='Collar Style')
        
        if customization.cuff_style:
            draw_custom_item("Cuff Style", "نمط الكم",
                           customization.cuff_style.value,
                           customization.cuff_style.asset_path,
                           label_ur='Cuff Style')
        
        if customization.pocket_style:
            draw_custom_item("Pocket Style", "نمط الجيب",
                           customization.pocket_style.value,
                           customization.pocket_style.asset_path,
                           label_ur='Pocket Style')
        
        self.y_position -= 5 * mm
    
    def draw_notes(self):
        """Draw custom notes section"""
        if not self.order.custom_notes:
            return
        
        self.pdf.setFont("Helvetica-Bold", 12)
        title = self._label("Special Instructions", "تعليمات خاصة")
        self.pdf.drawString(self.MARGIN, self.y_position, self.render_text(title))
        self.y_position -= 7 * mm
        
        self.pdf.setFont("Helvetica", 10)
        notes = self.render_text(self.order.custom_notes)
        self.pdf.drawString(self.MARGIN, self.y_position, notes)
        self.y_position -= 10 * mm
    
    def generate(self):
        """Generate the complete PDF and return bytes"""
        # Draw all sections
        self.draw_header()
        self.draw_customer_info()
        
        # Draw info for each order item
        for item in self.order.order_items.all():
            if self.y_position < 100 * mm:  # New page if running out of space
                self.pdf.showPage()
                self.y_position = self.PAGE_HEIGHT - self.MARGIN
            
            self.draw_measurements(item)
            self.draw_fabric_info(item)
            self.draw_customizations(item)
        
        self.draw_notes()
        
        # Save PDF
        self.pdf.save()
        
        # Get PDF bytes
        pdf_bytes = self.buffer.getvalue()
        self.buffer.close()
        
        return pdf_bytes
