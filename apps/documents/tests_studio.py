from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings

from apps.customization.models import MeasurementField, MeasurementTemplate
from apps.customers.models import CustomerProfile
from apps.documents.catalog import CUSTOMER, HEADER, PERSON_ITEMS
from apps.documents.models import PdfDocumentSection, PdfDocumentTemplate
from apps.orders.models import Order, OrderItem
from apps.tailors.models import Fabric, FabricCategory, TailorProfile

User = get_user_model()


class PdfLayoutStudioTest(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username='studio_staff',
            password='testpass123',
            role='ADMIN',
            is_staff=True,
        )
        self.client = Client()
        self.client.force_login(self.staff)

        self.customer = User.objects.create_user(
            username='studio_customer',
            password='testpass123',
            role='USER',
            first_name='Ahmed',
        )
        CustomerProfile.objects.create(user=self.customer)
        self.tailor_user = User.objects.create_user(
            username='studio_tailor',
            password='testpass123',
            role='TAILOR',
        )
        self.tailor_profile, _ = TailorProfile.objects.get_or_create(
            user=self.tailor_user,
            defaults={'shop_name': 'Test Shop', 'shop_status': True},
        )
        category = FabricCategory.objects.create(name='Fabric', slug='studio-fabric')
        fabric = Fabric.objects.create(
            tailor=self.tailor_profile,
            name='Gray',
            price=Decimal('100'),
            stock=5,
            is_active=True,
            category=category,
        )
        self.order = Order.objects.create(
            customer=self.customer,
            tailor=self.tailor_user,
            order_type='fabric_with_stitching',
            payment_method='cod',
            subtotal=Decimal('100'),
            total_amount=Decimal('100'),
        )
        OrderItem.objects.create(
            order=self.order,
            fabric=fabric,
            quantity=1,
            unit_price=Decimal('100'),
            total_price=Decimal('100'),
            measurements={'chest': 42, 'waist': 34, 'unit': 'cm', '_order': ['chest', 'waist']},
        )

    def test_studio_page_requires_staff(self):
        anon = Client()
        response = anon.get('/studio/pdf-layout/')
        self.assertEqual(response.status_code, 302)

    def test_studio_page_loads_for_staff(self):
        response = self.client.get('/studio/pdf-layout/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'PDF Layout Studio')
        self.assertContains(response, 'grid-modal')
        self.assertContains(response, 'Save grid')
        self.assertContains(response, 'Edit measurement grid')
        self.assertContains(response, 'Unplaced fields')
        self.assertContains(response, 'lang-switch')
        self.assertContains(response, 'العربية')
        self.assertContains(response, 'اردو')

    def test_api_load_includes_localized_measurement_labels(self):
        response = self.client.get('/studio/pdf-layout/api/')
        self.assertEqual(response.status_code, 200)
        fields = response.json()['measurement_fields']
        self.assertGreater(len(fields), 0)
        sample = fields[0]
        self.assertIn('display_name_ar', sample)
        self.assertIn('display_name_ur', sample)
        self.assertIn('pdf_label_en', sample)
        self.assertEqual(sample['pdf_label_en'], (sample['display_name'] or '').upper())
        with_ar = [f for f in fields if f.get('display_name_ar')]
        self.assertGreater(len(with_ar), 0, 'Expected Arabic labels on measurement fields')

    def test_api_load_returns_sections_and_fields(self):
        response = self.client.get('/studio/pdf-layout/api/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('sections', data)
        self.assertIn('measurement_fields', data)
        self.assertGreaterEqual(len(data['sections']), 8)

    def test_save_section_order_and_visibility(self):
        template = PdfDocumentTemplate.objects.get(is_default=True)
        customer_section = template.sections.get(key=CUSTOMER)
        customer_section.is_visible = True
        customer_section.save()

        sections = list(template.sections.order_by('display_order'))
        first = sections[0]
        second = sections[1]
        payload = {
            'sections': [
                {'id': first.id, 'display_order': 2, 'is_visible': True, 'settings': first.settings or {}},
                {'id': second.id, 'display_order': 1, 'is_visible': False, 'settings': second.settings or {}},
            ],
        }
        response = self.client.put(
            '/studio/pdf-layout/api/save/',
            data=payload,
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        second.refresh_from_db()
        self.assertEqual(second.display_order, 1)
        self.assertFalse(second.is_visible)

    def test_save_measurement_grid(self):
        thobe = MeasurementTemplate.objects.filter(name='thobe').first()
        if thobe is None:
            self.skipTest('Thobe template not seeded')
        field = MeasurementField.objects.filter(template=thobe).order_by('display_order').first()
        response = self.client.put(
            '/studio/pdf-layout/api/measurements/',
            data={
                'fields': [{
                    'id': field.id,
                    'display_order': 1,
                    'pdf_grid_row': 2,
                    'pdf_grid_col': 3,
                }],
            },
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        field.refresh_from_db()
        self.assertEqual(field.pdf_grid_row, 2)
        self.assertEqual(field.pdf_grid_col, 3)

    def test_swap_two_measurement_fields(self):
        thobe = MeasurementTemplate.objects.filter(name='thobe').first()
        if thobe is None:
            self.skipTest('Thobe template not seeded')
        fields = list(
            MeasurementField.objects.filter(template=thobe, is_active=True)
            .order_by('display_order')[:2]
        )
        if len(fields) < 2:
            self.skipTest('Need at least two thobe measurement fields')

        first, second = fields
        first_pos = (first.pdf_grid_row, first.pdf_grid_col)
        second_pos = (second.pdf_grid_row, second.pdf_grid_col)

        response = self.client.put(
            '/studio/pdf-layout/api/measurements/',
            data={
                'fields': [
                    {
                        'id': first.id,
                        'display_order': 2,
                        'pdf_grid_row': second_pos[0],
                        'pdf_grid_col': second_pos[1],
                    },
                    {
                        'id': second.id,
                        'display_order': 1,
                        'pdf_grid_row': first_pos[0],
                        'pdf_grid_col': first_pos[1],
                    },
                ],
            },
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual((first.pdf_grid_row, first.pdf_grid_col), second_pos)
        self.assertEqual((second.pdf_grid_row, second.pdf_grid_col), first_pos)
        self.assertEqual(second.display_order, 1)
        self.assertEqual(first.display_order, 2)

    def test_preview_reflects_swapped_measurement_grid(self):
        thobe = MeasurementTemplate.objects.filter(name='thobe').first()
        if thobe is None:
            self.skipTest('Thobe template not seeded')
        fields = list(
            MeasurementField.objects.filter(template=thobe, is_active=True)
            .order_by('display_order')[:2]
        )
        if len(fields) < 2:
            self.skipTest('Need at least two thobe measurement fields')

        first, second = fields
        template = PdfDocumentTemplate.objects.get(is_default=True)
        sections = [
            {
                'key': s.key,
                'display_order': s.display_order,
                'is_visible': True,
                'settings': s.settings or {},
            }
            for s in template.sections.order_by('display_order')
        ]
        draft_fields = [
            {
                'name': first.name,
                'display_order': 2,
                'pdf_grid_row': second.pdf_grid_row,
                'pdf_grid_col': second.pdf_grid_col,
            },
            {
                'name': second.name,
                'display_order': 1,
                'pdf_grid_row': first.pdf_grid_row,
                'pdf_grid_col': first.pdf_grid_col,
            },
        ]
        response = self.client.post(
            '/studio/pdf-layout/preview/',
            data={
                'order_id': self.order.id,
                'lang': 'en',
                'sections': sections,
                'measurement_fields': draft_fields,
            },
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/html', response['Content-Type'])

    def test_preview_with_draft_sections(self):
        template = PdfDocumentTemplate.objects.get(is_default=True)
        sections = [
            {
                'key': s.key,
                'display_order': s.display_order,
                'is_visible': s.key != CUSTOMER,
                'settings': s.settings or {},
            }
            for s in template.sections.order_by('display_order')
        ]
        response = self.client.post(
            '/studio/pdf-layout/preview/',
            data={
                'order_id': self.order.id,
                'lang': 'en',
                'sections': sections,
            },
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/html', response['Content-Type'])
        self.assertNotIn(b'CUSTOMER INFORMATION', response.content)

    def test_preview_respects_draft_section_display_order(self):
        template = PdfDocumentTemplate.objects.get(is_default=True)
        last_order = template.sections.count()
        sections = [
            {
                'key': s.key,
                'display_order': last_order if s.key == HEADER else s.display_order,
                'is_visible': True,
                'settings': s.settings or {},
            }
            for s in template.sections.order_by('display_order')
        ]
        response = self.client.post(
            '/studio/pdf-layout/preview/',
            data={
                'order_id': self.order.id,
                'lang': 'en',
                'sections': sections,
            },
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        customer_pos = html.find('CUSTOMER INFORMATION')
        banner_pos = html.find('class="banner"')
        self.assertNotEqual(customer_pos, -1)
        self.assertNotEqual(banner_pos, -1)
        self.assertLess(customer_pos, banner_pos, 'Header should render after customer when moved last')

    def test_person_items_settings_save(self):
        template = PdfDocumentTemplate.objects.get(is_default=True)
        person = template.sections.get(key=PERSON_ITEMS)
        response = self.client.put(
            '/studio/pdf-layout/api/save/',
            data={
                'sections': [{
                    'id': person.id,
                    'display_order': person.display_order,
                    'is_visible': True,
                    'settings': {
                        'show_fabric': True,
                        'show_measurements': False,
                        'measurement_cols': 5,
                        'measurement_rows': 4,
                    },
                }],
            },
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        person.refresh_from_db()
        self.assertFalse(person.settings.get('show_measurements'))
