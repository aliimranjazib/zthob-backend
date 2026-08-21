from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.customization.models import MeasurementField, MeasurementTemplate
from apps.customers.models import CustomerProfile, FamilyMember
from apps.documents.catalog import CUSTOMER, HEADER, PERSON_ITEMS, default_sections
from apps.documents.context import build_order_document_context
from apps.documents.layout import resolve_layout
from apps.documents.models import PdfDocumentSection, PdfDocumentTemplate
from apps.documents.service import generate_order_document, generate_order_html
from apps.orders.models import Order, OrderItem
from apps.tailors.models import Fabric, FabricCategory, TailorProfile

User = get_user_model()


class OrderDocumentEngineTest(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(
            username='doc_customer',
            password='testpass123',
            role='USER',
            first_name='Ahmed',
            last_name='Al-Saud',
            phone='0501111999',
        )
        CustomerProfile.objects.create(user=self.customer)
        self.tailor_user = User.objects.create_user(
            username='doc_tailor',
            password='testpass123',
            role='TAILOR',
        )
        self.tailor_profile, _ = TailorProfile.objects.get_or_create(
            user=self.tailor_user,
            defaults={'shop_name': 'Al Jeel Stitched', 'shop_status': True},
        )
        category = FabricCategory.objects.create(name='Fabric', slug='doc-fabric')
        fabric = Fabric.objects.create(
            tailor=self.tailor_profile,
            name='Light Gray Casual',
            price=Decimal('100.00'),
            stock=10,
            is_active=True,
            category=category,
            sku='FAB-81568613',
        )
        self.order = Order.objects.create(
            customer=self.customer,
            tailor=self.tailor_user,
            order_type='fabric_with_stitching',
            payment_method='cod',
            service_mode='walk_in',
            subtotal=Decimal('100.00'),
            total_amount=Decimal('100.00'),
        )
        family = FamilyMember.objects.create(user=self.customer, name='Ali', relationship='son')
        OrderItem.objects.create(
            order=self.order,
            fabric=fabric,
            quantity=1,
            unit_price=Decimal('100.00'),
            total_price=Decimal('100.00'),
            family_member=family,
            measurements={
                'sleeve_width': 16,
                'takhalis': 17,
                'waist': 9,
                'teek': 20,
                'unit': 'cm',
                '_order': ['sleeve_width', 'takhalis', 'waist', 'teek'],
            },
            custom_instructions='test 4',
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.tailor_user)

    def test_default_template_is_seeded_with_all_sections(self):
        template = PdfDocumentTemplate.objects.get(slug='order_receipt', version=1)
        self.assertTrue(template.is_default)
        keys = list(template.sections.order_by('display_order').values_list('key', flat=True))
        self.assertEqual(keys, [item['key'] for item in default_sections()])

    def test_html_contains_full_document_and_omits_customer_phone(self):
        html, context, layout = generate_order_html(self.order, lang='en')
        self.assertIn(self.order.order_number, html)
        self.assertIn('Ahmed Al-Saud', html)
        self.assertIn('Ali', html)
        self.assertIn('Light Gray Casual', html)
        self.assertIn('CUSTOMER INFORMATION', html)
        self.assertIn('ORDER ITEMS BY PERSON', html)
        self.assertNotIn('0501111999', html)
        self.assertNotIn('0501111999', context['customer']['name'])
        self.assertEqual(layout.sections[0].key, HEADER)

    def test_hidden_section_is_omitted_from_html(self):
        template = PdfDocumentTemplate.objects.get(slug='order_receipt', version=1)
        PdfDocumentSection.objects.filter(template=template, key=CUSTOMER).update(is_visible=False)
        html, _context, layout = generate_order_html(self.order, lang='en')
        self.assertNotIn(CUSTOMER, [section.key for section in layout.sections])
        self.assertNotIn('CUSTOMER INFORMATION', html)

    def test_measurement_cells_use_client_grid_when_configured(self):
        thobe = MeasurementTemplate.objects.filter(name='thobe').first()
        if thobe is None:
            self.skipTest('Thobe measurement template was not seeded')
        MeasurementField.objects.filter(template=thobe, name='sleeve_width').update(
            pdf_grid_row=1, pdf_grid_col=1, display_order=1,
        )
        MeasurementField.objects.filter(template=thobe, name='waist').update(
            pdf_grid_row=4, pdf_grid_col=1, display_order=3,
        )
        layout = resolve_layout()
        context = build_order_document_context(self.order, 'en', layout)
        cells = {cell['key']: cell for cell in context['items'][0]['measurement_cells']}
        self.assertEqual(cells['sleeve_width']['row'], 1)
        self.assertEqual(cells['sleeve_width']['col'], 1)
        self.assertEqual(cells['waist']['row'], 4)
        self.assertEqual(cells['waist']['col'], 1)
        html, _ctx, _layout = generate_order_html(self.order, lang='en')
        table = context['items'][0]['measurement_table']
        self.assertEqual(table[3][0]['key'], 'waist')
        self.assertIn('meas-grid-table', html)
        self.assertIn('Sleeve Width', html)

    def test_measurement_grid_shows_all_slots_including_empty(self):
        thobe = MeasurementTemplate.objects.filter(name='thobe').first()
        if thobe is None:
            self.skipTest('Thobe measurement template was not seeded')
        for index, field in enumerate(
            MeasurementField.objects.filter(template=thobe, is_active=True).order_by('display_order')[:20],
            start=1,
        ):
            row = ((index - 1) % 4) + 1
            col = ((index - 1) // 4) + 1
            field.pdf_grid_row = row
            field.pdf_grid_col = col
            field.display_order = index
            field.save(update_fields=['pdf_grid_row', 'pdf_grid_col', 'display_order', 'updated_at'])

        layout = resolve_layout()
        context = build_order_document_context(self.order, 'en', layout)
        cells = context['items'][0]['measurement_cells']
        self.assertEqual(len(cells), 20)
        empty_cells = [cell for cell in cells if not cell.get('has_value') and cell.get('label')]
        self.assertGreater(len(empty_cells), 0)
        html, _ctx, _layout = generate_order_html(self.order, lang='en')
        self.assertIn('—', html)

    def test_arabic_html_uses_rtl_and_arabic_labels(self):
        html, context, _layout = generate_order_html(self.order, lang='ar')
        self.assertTrue(context['is_rtl'])
        self.assertIn('dir="rtl"', html)
        self.assertIn('doc-rtl', html)
        self.assertIn('معلومات العميل', html)
        self.assertNotIn('meas-grid meas-grid-fixed-cols', html)
        self.assertIn('meas-grid-table', html)
        self.assertIn('dir="rtl"', html)
        self.assertIn('text-transform: none', html)

    @override_settings(ORDER_PDF_ENGINE='reportlab')
    def test_document_engine_can_fall_back_to_reportlab(self):
        pdf_bytes = generate_order_document(self.order, lang='en', engine='reportlab')
        self.assertTrue(pdf_bytes.startswith(b'%PDF'))
        self.assertNotIn(b'0501111999', pdf_bytes)

    @override_settings(SECURE_SSL_REDIRECT=False)
    def test_html_preview_endpoint(self):
        response = self.client.get(
            f'/api/tailors/orders/{self.order.id}/document-preview/?lang=en',
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/html', response['Content-Type'])
        self.assertIn(self.order.order_number.encode(), response.content)
        self.assertNotIn(b'0501111999', response.content)

    def test_person_item_settings_can_hide_measurements(self):
        template = PdfDocumentTemplate.objects.get(slug='order_receipt', version=1)
        section = template.sections.get(key=PERSON_ITEMS)
        settings = dict(section.settings or {})
        settings['show_measurements'] = False
        section.settings = settings
        section.save(update_fields=['settings'])
        html, context, _layout = generate_order_html(self.order, lang='en')
        self.assertFalse(context['layout']['person']['show_measurements'])
        self.assertNotIn('grid-row:', html)
        self.assertNotIn('Sleeve Width', html)
