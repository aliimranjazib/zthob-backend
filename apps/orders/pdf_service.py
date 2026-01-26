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
            language: 'ar' for Arabic, 'en' for English
        """
        self.order = order
        self.language = language
        self.buffer = BytesIO()
        self.pdf = canvas.Canvas(self.buffer, pagesize=A4)
        self.y_position = self.PAGE_HEIGHT - self.MARGIN
        
    def render_text(self, text, is_arabic=None):
        """
        Render text with proper Arabic RTL handling
        
        Args:
            text: Text to render
            is_arabic: Force Arabic rendering, auto-detect if None
        """
        if is_arabic is None:
            is_arabic = self.language == 'ar'
        
        if is_arabic and text:
            reshaped = reshape(str(text))
            return get_display(reshaped)
        return str(text)
    
    def draw_header(self):
        """Draw PDF header with order info"""
        # Title
        self.pdf.setFont("Helvetica-Bold", 18)
        title = "Work Order" if self.language == 'en' else "أمر العمل"
        title_rendered = self.render_text(title)
        self.pdf.drawCentredString(self.PAGE_WIDTH / 2, self.y_position, title_rendered)
        self.y_position -= 10 * mm
        
        # Order number
        self.pdf.setFont("Helvetica-Bold", 14)
        order_num = f"Order #{self.order.order_number}"
        if self.language == 'ar':
            order_num = f"#{self.order.order_number} الطلب رقم"
        order_num_rendered = self.render_text(order_num)
        self.pdf.drawCentredString(self.PAGE_WIDTH / 2, self.y_position, order_num_rendered)
        self.y_position -= 15 * mm
        
        # Horizontal line
        self.pdf.line(self.MARGIN, self.y_position, self.PAGE_WIDTH - self.MARGIN, self.y_position)
        self.y_position -= 5 * mm
        
    def draw_customer_info(self):
        """Draw customer information section"""
        self.pdf.setFont("Helvetica-Bold", 12)
        section_title = "Customer Information" if self.language == 'en' else "معلومات العميل"
        self.pdf.drawString(self.MARGIN, self.y_position, self.render_text(section_title))
        self.y_position -= 7 * mm
        
        self.pdf.setFont("Helvetica", 10)
        
        # Customer name
        customer_name = self.order.customer.username if self.order.customer else "N/A"
        name_label = "Customer:" if self.language == 'en' else ":العميل"
        self.pdf.drawString(self.MARGIN, self.y_position, 
                          self.render_text(f"{name_label} {customer_name}"))
        self.y_position -= 5 * mm
        
        # Phone
        phone = self.order.customer.phone_number if self.order.customer else "N/A"
        phone_label = "Phone:" if self.language == 'en' else ":الهاتف"
        self.pdf.drawString(self.MARGIN, self.y_position,
                          self.render_text(f"{phone_label} {phone}"))
        self.y_position -= 5 * mm
        
        # Service mode
        service_label = "Service:" if self.language == 'en' else ":الخدمة"
        service_val = "Home Delivery" if self.order.service_mode == 'home_delivery' else "Walk-in"
        if self.language == 'ar':
            service_val = "توصيل منزلي" if self.order.service_mode == 'home_delivery' else "استلام من المحل"
        self.pdf.drawString(self.MARGIN, self.y_position,
                          self.render_text(f"{service_label} {service_val}"))
        self.y_position -= 10 * mm
        
    def draw_measurements(self, order_item):
        """Draw measurements table for an order item"""
        if not order_item.measurements:
            return
        
        self.pdf.setFont("Helvetica-Bold", 12)
        title = "Measurements" if self.language == 'en' else "القياسات"
        self.pdf.drawString(self.MARGIN, self.y_position, self.render_text(title))
        self.y_position -= 7 * mm
        
        # Build measurements table data
        table_data = []
        measurements = order_item.measurements
        
        # Measurement labels
        meas_labels = {
            'neck': ('Neck', 'الرقبة'),
            'shoulder': ('Shoulder', 'الكتف'),
            'chest': ('Chest', 'الصدر'),
            'waist': ('Waist', 'الخصر'),
            'hip': ('Hip', 'الورك'),
            'sleeve_length': ('Sleeve Length', 'طول الكم'),
            'arm_hole': ('Arm Hole', 'فتحة الذراع'),
            'body_length': ('Body Length', 'طول الجسم'),
            'thobe_length': ('Thobe Length', 'طول الثوب'),
        }
        
        row = []
        for key, (en_label, ar_label) in meas_labels.items():
            if key in measurements and measurements[key]:
                label = ar_label if self.language == 'ar' else en_label
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
        title = "Fabric Details" if self.language == 'en' else "تفاصيل القماش"
        self.pdf.drawString(self.MARGIN, self.y_position, self.render_text(title))
        self.y_position -= 7 * mm
        
        self.pdf.setFont("Helvetica", 10)
        fabric = order_item.fabric
        
        # Fabric name
        fabric_label = "Fabric:" if self.language == 'en' else ":القماش"
        self.pdf.drawString(self.MARGIN, self.y_position,
                          self.render_text(f"{fabric_label} {fabric.name}"))
        self.y_position -= 5 * mm
        
        # Color
        color_label = "Color:" if self.language == 'en' else ":اللون"
        self.pdf.drawString(self.MARGIN, self.y_position,
                          self.render_text(f"{color_label} {fabric.color}"))
        self.y_position -= 10 * mm
    
    def draw_customizations(self, order_item):
        """Draw customization details with images"""
        if not hasattr(order_item, 'customization') or not order_item.customization:
            return
        
        self.pdf.setFont("Helvetica-Bold", 12)
        title = "Customization" if self.language == 'en' else "التخصيص"
        self.pdf.drawString(self.MARGIN, self.y_position, self.render_text(title))
        self.y_position -= 7 * mm
        
        self.pdf.setFont("Helvetica", 10)
        customization = order_item.customization
        
        # Helper to draw customization with optional image
        def draw_custom_item(label_en, label_ar, value, image_path=None):
            label = label_ar if self.language == 'ar' else label_en
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
                           customization.collar_style.asset_path)
        
        if customization.cuff_style:
            draw_custom_item("Cuff Style", "نمط الكم",
                           customization.cuff_style.value,
                           customization.cuff_style.asset_path)
        
        if customization.pocket_style:
            draw_custom_item("Pocket Style", "نمط الجيب",
                           customization.pocket_style.value,
                           customization.pocket_style.asset_path)
        
        self.y_position -= 5 * mm
    
    def draw_notes(self):
        """Draw custom notes section"""
        if not self.order.custom_notes:
            return
        
        self.pdf.setFont("Helvetica-Bold", 12)
        title = "Special Instructions" if self.language == 'en' else "تعليمات خاصة"
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
