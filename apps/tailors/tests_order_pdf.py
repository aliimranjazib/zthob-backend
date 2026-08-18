from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.customers.models import CustomerProfile, FamilyMember
from apps.orders.models import Order, OrderItem
from apps.tailors.models import Fabric, FabricCategory, TailorProfile
from apps.tailors.services.order_pdf import (
    _ARABIC_FONT_AVAILABLE,
    _build_customer_section,
    _build_order_details_section,
    _build_person_blocks,
    _build_priority_sections,
    _build_riders_section,
    _canvas_customer_summary_line,
    _pdf_page_width,
    _measurement_taken_by_name,
    _rider_contact_details,
    _contains_arabic,
    _custom_style_caption_html,
    _custom_style_comment_html,
    _format_label_html,
    _format_measurement_pairs,
    _format_recipient_html,
    _format_user_text_html,
    _item_recipient_display,
    _measurement_grid_rows,
    _normalize_rtl_text,
    _resolve_media_file_path,
    _shape_arabic,
    _safe_text,
    _styles,
    _style_reference_image_paths,
    _t,
    _translate_label,
    _truncate_style_comment,
    generate_order_pdf,
)

User = get_user_model()


class OrderPDFServiceTest(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(
            username='pdf_customer',
            password='testpass123',
            role='USER',
            first_name='Ahmed',
            last_name='Al-Saud',
        )
        CustomerProfile.objects.create(user=self.customer)

        self.tailor_user = User.objects.create_user(
            username='pdf_tailor',
            password='testpass123',
            role='TAILOR',
        )
        self.tailor_profile, _ = TailorProfile.objects.get_or_create(
            user=self.tailor_user,
            defaults={
                'shop_name': 'محل الخياطة',
                'shop_status': True,
            },
        )

        self.fabric_category = FabricCategory.objects.create(name='Fabric', slug='fabric-pdf')
        self.fabric = Fabric.objects.create(
            tailor=self.tailor_profile,
            name='قماش قطني فاخر',
            price=Decimal('100.00'),
            stock=10,
            is_active=True,
            category=self.fabric_category,
        )

        self.order = Order.objects.create(
            customer=self.customer,
            tailor=self.tailor_user,
            order_type='fabric_with_stitching',
            payment_method='cod',
            subtotal=Decimal('100.00'),
            total_amount=Decimal('100.00'),
        )
        self.family_member = FamilyMember.objects.create(
            user=self.customer,
            name='Ali',
            relationship='son',
        )
        OrderItem.objects.create(
            order=self.order,
            fabric=self.fabric,
            quantity=1,
            unit_price=Decimal('100.00'),
            total_price=Decimal('100.00'),
            family_member=self.family_member,
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.tailor_user)

    def test_measurement_arabic_label_not_double_shaped(self):
        pairs = _format_measurement_pairs(
            {'sleeve_length': 24, 'chest_front': 42},
            lang='ar',
            field_map={
                'sleeve_length': {
                    'label_en': 'Sleeve Length',
                    'label_ar': 'طول الكم',
                    'order': 0,
                    'unit': 'cm',
                },
                'chest_front': {
                    'label_en': 'Chest Front',
                    'label_ar': 'الصدر الأمامي',
                    'order': 1,
                    'unit': 'cm',
                },
            },
        )
        self.assertEqual(len(pairs), 2)
        shaped_once = pairs[0][0]
        shaped_twice = _shape_arabic(_shape_arabic('طول الكم'))
        self.assertEqual(shaped_once, _shape_arabic('طول الكم'))
        self.assertNotEqual(shaped_once, shaped_twice)

    def test_format_measurement_pairs_follows_stored_order_when_keys_scrambled(self):
        pairs = _format_measurement_pairs(
            {
                'waist': 34,
                'shoulder': 18,
                'chest': 42,
                '_order': ['chest', 'waist', 'shoulder'],
            },
            lang='en',
            field_map={},
        )
        self.assertEqual([pair[0] for pair in pairs], ['Chest', 'Waist', 'Shoulder'])
        self.assertEqual([pair[1] for pair in pairs], [42, 34, 18])

    def test_format_measurement_pairs_skips_empty_null_and_metadata(self):
        pairs = _format_measurement_pairs(
            {
                'chest': 42,
                'waist': None,
                'hip': '',
                'sleeve_length': 'null',
                'title': 'Wedding Thobe',
                'unit': 'cm',
                '_order': ['chest', 'waist', 'hip', 'sleeve_length'],
            },
            lang='en',
            field_map={},
        )
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0][0], 'Chest')
        self.assertEqual(pairs[0][1], 42)

    def test_rtl_measurement_grid_fills_down_the_right_column(self):
        from apps.tailors.services.order_pdf import PDF_MEASUREMENT_COLS

        pairs = [(str(i), i) for i in range(1, 21)]
        grid = _measurement_grid_rows(pairs, PDF_MEASUREMENT_COLS, is_rtl=True)
        self.assertEqual(len(grid), 4)
        self.assertEqual(len(grid[0]), PDF_MEASUREMENT_COLS)
        # Arabic reads down the rightmost column first: 1, 2, 3, 4.
        self.assertEqual([row[-1] for row in grid], [('1', 1), ('2', 2), ('3', 3), ('4', 4)])
        self.assertEqual([row[-2] for row in grid], [('5', 5), ('6', 6), ('7', 7), ('8', 8)])

    def test_ltr_measurement_grid_fills_down_the_left_column(self):
        from apps.tailors.services.order_pdf import PDF_MEASUREMENT_COLS

        pairs = [(str(i), i) for i in range(1, 8)]
        grid = _measurement_grid_rows(pairs, PDF_MEASUREMENT_COLS, is_rtl=False)
        self.assertEqual([row[0] for row in grid], [('1', 1), ('2', 2)])
        self.assertEqual([row[1] for row in grid], [('3', 3), ('4', 4)])
        self.assertEqual(grid[0][3], ('7', 7))
        self.assertEqual(grid[1][3], ('', ''))

    def test_pdf_priority_sections_appear_before_order_details(self):
        item = self.order.order_items.first()
        item.measurements = {'chest': 42, 'waist': 34}
        item.save(update_fields=['measurements'])

        from reportlab.lib.units import mm

        s = _styles('en')
        page_w = _pdf_page_width()
        items = list(self.order.order_items.select_related('fabric', 'family_member').all())
        priority = _build_priority_sections(self.order, items, page_w, s, 'en', {})
        details = _build_order_details_section(self.order, page_w, s, 'en')
        customer = _build_customer_section(self.order, page_w, s, 'en')
        self.assertGreater(len(priority), 0)
        self.assertGreater(len(details), 0)
        self.assertGreater(len(customer), 0)

    def test_person_block_includes_fabric_and_quantity(self):
        item = self.order.order_items.first()
        item.measurements = {'chest': 42, 'waist': 34}
        item.quantity = 2
        item.save(update_fields=['measurements', 'quantity'])

        s = _styles('en')
        page_w = _pdf_page_width()
        items = list(self.order.order_items.select_related('fabric', 'family_member').all())
        blocks = _build_person_blocks(self.order, items, page_w, s, 'en', {})
        joined = ' '.join(getattr(el, 'text', str(el)) for el in blocks)
        self.assertIn('ALI', joined.upper())
        self.assertIn('Qty', joined)

    def test_riders_section_shows_measurement_and_delivery_contacts(self):
        meas_rider = User.objects.create_user(
            username='meas_rider_pdf',
            password='testpass123',
            role='RIDER',
            phone='+966500000001',
        )
        del_rider = User.objects.create_user(
            username='del_rider_pdf',
            password='testpass123',
            role='RIDER',
            phone='+966500000002',
        )
        from apps.riders.models import RiderProfile
        RiderProfile.objects.create(user=meas_rider, full_name='Khalid Meas', phone_number='+966500000001')
        RiderProfile.objects.create(user=del_rider, full_name='Saeed Del', phone_number='+966500000002')
        self.order.measurement_rider = meas_rider
        self.order.delivery_rider = del_rider
        self.order.save(update_fields=['measurement_rider', 'delivery_rider'])

        s = _styles('en')
        section = _build_riders_section(self.order, _pdf_page_width(), s, 'en')
        joined = ' '.join(getattr(el, 'text', str(el)) for el in section)
        self.assertIn('Khalid Meas', joined)
        self.assertIn('Saeed Del', joined)
        self.assertIn('+966500000001', joined)
        self.assertIn('+966500000002', joined)

    def _story_text(self, story):
        return ' '.join(str(getattr(el, 'text', '')) for el in story)

    def test_customer_section_is_one_line_without_phone(self):
        self.customer.phone = '0501111999'
        self.customer.save(update_fields=['phone'])

        s = _styles('en')
        section = _build_customer_section(self.order, _pdf_page_width(), s, 'en')
        joined = self._story_text(section)

        self.assertIn('CUSTOMER INFORMATION', joined)
        self.assertIn('Name', joined)
        self.assertIn('Ahmed', joined)
        self.assertIn('Service Mode', joined)
        self.assertIn('Home Delivery', joined)
        self.assertNotIn('0501111999', joined)
        self.assertNotIn('Phone', joined)
        self.assertNotIn('Measured by', joined)
        self.assertEqual(sum(1 for el in section if getattr(el, 'text', '') and '|' in str(el.text)), 1)

    def test_customer_section_shows_walk_in_tailor_as_measured_by(self):
        self.order.service_mode = 'walk_in'
        self.order.measurement_taken_at = timezone.now()
        self.order.save(update_fields=['service_mode', 'measurement_taken_at'])

        self.assertEqual(_measurement_taken_by_name(self.order), 'pdf_tailor')
        section = _build_customer_section(self.order, _pdf_page_width(), _styles('en'), 'en')
        joined = self._story_text(section)
        self.assertIn('Measured by', joined)
        self.assertIn('pdf_tailor', joined)
        self.assertIn('Walk-In Service', joined)

    def test_customer_section_shows_measurement_rider_as_measured_by(self):
        meas_rider = User.objects.create_user(
            username='pdf_meas_by_rider',
            password='testpass123',
            role='RIDER',
        )
        from apps.riders.models import RiderProfile
        RiderProfile.objects.create(user=meas_rider, full_name='Khalid Meas')
        self.order.measurement_rider = meas_rider
        self.order.measurement_taken_at = timezone.now()
        self.order.save(update_fields=['measurement_rider', 'measurement_taken_at'])

        self.assertEqual(_measurement_taken_by_name(self.order), 'Khalid Meas')
        section = _build_customer_section(self.order, _pdf_page_width(), _styles('en'), 'en')
        joined = self._story_text(section)
        self.assertIn('Measured by', joined)
        self.assertIn('Khalid Meas', joined)

    def test_customer_section_arabic_uses_measured_by_label(self):
        self.order.service_mode = 'walk_in'
        self.order.measurement_taken_at = timezone.now()
        self.order.save(update_fields=['service_mode', 'measurement_taken_at'])

        section = _build_customer_section(self.order, _pdf_page_width(), _styles('ar'), 'ar')
        joined = self._story_text(section)
        self.assertIn(_t('Measured by', 'ar'), joined)
        self.assertIn(_t('Name', 'ar'), joined)
        self.assertEqual(_translate_label('Measured by', 'ar'), 'تم القياس بواسطة')
        self.assertEqual(_translate_label('Measured by', 'ur'), 'ناپ لینے والا')

    def test_generated_pdf_omits_customer_phone_from_header_and_body(self):
        self.customer.phone = '0501111999'
        self.customer.save(update_fields=['phone'])

        self.assertNotIn('0501111999', _canvas_customer_summary_line(self.order, 'en'))
        pdf_bytes = generate_order_pdf(self.order, lang='en')
        self.assertTrue(pdf_bytes.startswith(b'%PDF'))
        self.assertNotIn(b'0501111999', pdf_bytes)

    def test_pdf_includes_page_number_marker(self):
        pdf_bytes = generate_order_pdf(self.order, lang='en')
        self.assertTrue(pdf_bytes.startswith(b'%PDF'))
        self.assertIn(b'Page', pdf_bytes)

    @override_settings(SECURE_SSL_REDIRECT=False)
    def test_download_pdf_lang_query_param_overrides_default(self):
        response = self.client.get(
            f'/api/tailors/orders/{self.order.id}/download-pdf/?lang=en',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF'))

    def test_arabic_fonts_are_available(self):
        self.assertTrue(_ARABIC_FONT_AVAILABLE)

    def test_contains_arabic_detects_arabic_script(self):
        self.assertTrue(_contains_arabic('قماش'))
        self.assertFalse(_contains_arabic('Cotton Fabric'))

    def test_english_pdf_embeds_arabic_font_for_arabic_user_content(self):
        html = _format_user_text_html('قماش قطني', lang='en')
        self.assertIn('IBMPlexSansArabic-Regular', html)

    def test_mixed_arabic_english_preserves_latin_name(self):
        html = _format_user_text_html('لصالح: farhan', lang='ar')
        self.assertIn('farhan', html)

    def test_pre_shaped_arabic_is_not_double_processed(self):
        once = _t('Fabric + Stitching', lang='ar')
        html = _format_user_text_html(once, lang='ar', reshape=False)
        self.assertIn('IBMPlexSansArabic-Regular', html)
        twice = _shape_arabic(_shape_arabic('قماش مع خياطة'))
        self.assertNotEqual(once, twice)

    def test_reference_photos_label_not_double_shaped(self):
        logical = _translate_label('Reference Photos', lang='ar')
        shaped_once = _shape_arabic(logical)
        shaped_twice = _shape_arabic(shaped_once)
        html = _format_label_html('Reference Photos', lang='ar')
        self.assertEqual(shaped_once, _t('Reference Photos', lang='ar'))
        self.assertNotEqual(shaped_once, shaped_twice)
        self.assertIn('IBMPlexSansArabic-Regular', html)

    def test_custom_style_comment_uses_logical_label_before_shaping(self):
        logical_lbl = _translate_label('Comment', lang='ar')
        shaped_lbl = _shape_arabic(logical_lbl)
        html = _custom_style_comment_html({'text': 'تعليق تجريبي'}, lang='ar')
        self.assertIn('IBMPlexSansArabic-Regular', html)
        self.assertNotEqual(_shape_arabic(shaped_lbl), shaped_lbl)
        self.assertIn(_safe_text(shaped_lbl), html)

    def test_arabic_comment_label_is_not_reversed(self):
        html = _custom_style_comment_html({'text': 'السلام علیکم'}, lang='ar')
        shaped_comment_label = _safe_text(_shape_arabic('تعليق'))
        self.assertIn(shaped_comment_label, html)
        self.assertIn(_safe_text(_shape_arabic('علیکم')), html)
        self.assertNotIn(_safe_text(_shape_arabic('يقعلت')), html)

    def test_normalize_rtl_text_strips_zero_width_and_collapses_spaces(self):
        dirty = 'صورة\u200c  \u200f مرجعية'
        self.assertEqual(_normalize_rtl_text(dirty), 'صورة مرجعية')

    def test_arabic_style_label_with_mixed_content_shapes_once(self):
        html = _format_user_text_html('Collar: ياقة صينية', lang='ar')
        once = _shape_arabic('ياقة صينية')
        twice = _shape_arabic(once)
        self.assertIn('Collar:', html)
        self.assertIn('IBMPlexSansArabic-Regular', html)
        self.assertNotEqual(once, twice)

    def test_format_recipient_html_keeps_family_name_readable(self):
        item = self.order.order_items.select_related('family_member').first()
        html = _format_recipient_html(item, self.order, lang='ar')
        self.assertIn('Ali', html)
        self.assertIn('son', html)

    def test_item_recipient_display_uses_family_member(self):
        item = self.order.order_items.select_related('family_member').first()
        recipient = _item_recipient_display(item, self.order, lang='en')
        self.assertIn('Ali', recipient)
        self.assertIn('son', recipient)

    def test_generate_english_pdf_is_valid_and_includes_arabic_font(self):
        pdf_bytes = generate_order_pdf(self.order, lang='en')
        self.assertTrue(pdf_bytes.startswith(b'%PDF'))
        self.assertGreater(len(pdf_bytes), 1000)
        self.assertIn(b'IBMPlexSansArabic-Regular', pdf_bytes)

    def test_generate_arabic_pdf_returns_valid_pdf(self):
        pdf_bytes = generate_order_pdf(self.order, lang='ar')
        self.assertTrue(pdf_bytes.startswith(b'%PDF'))
        self.assertGreater(len(pdf_bytes), 1000)
        self.assertIn(b'IBMPlexSansArabic-Regular', pdf_bytes)

    def test_generate_urdu_pdf_returns_valid_pdf(self):
        pdf_bytes = generate_order_pdf(self.order, lang='ur')
        self.assertTrue(pdf_bytes.startswith(b'%PDF'))
        self.assertGreater(len(pdf_bytes), 1000)
        self.assertIn(b'IBMPlexSansArabic-Regular', pdf_bytes)

    def test_translate_label_to_urdu(self):
        self.assertNotEqual(_t('Order Receipt', 'ur'), 'Order Receipt')

    def test_customer_name_shown_when_item_has_no_family_member(self):
        item = self.order.order_items.first()
        item.family_member = None
        item.save(update_fields=['family_member'])

        recipient = _item_recipient_display(item, self.order, lang='en')
        self.assertIn('Ahmed Al-Saud', recipient)

        pdf_bytes = generate_order_pdf(self.order, lang='en')
        self.assertTrue(pdf_bytes.startswith(b'%PDF'))

    def test_custom_style_caption_includes_comment_in_english(self):
        html = _custom_style_caption_html({
            'style_type': 'collar',
            'label': 'Classic Collar',
            'text': 'Keep collar firm',
        }, lang='en')
        self.assertIn('Classic Collar', html)
        self.assertIn('Comment:', html)
        self.assertIn('Keep collar firm', html)

    def test_custom_style_caption_translates_comment_label_in_arabic(self):
        html = _custom_style_caption_html({
            'style_type': 'collar',
            'label': 'Classic Collar',
            'text': 'Keep collar firm',
        }, lang='ar')
        self.assertIn('Keep collar firm', html)
        self.assertIn('IBMPlexSansArabic-Regular', html)

    def test_truncate_style_comment_limits_very_long_text(self):
        long_text = 'word ' * 80
        truncated = _truncate_style_comment(long_text)
        self.assertLessEqual(len(truncated), 60)
        self.assertTrue(truncated.endswith('…'))

    def test_custom_style_comment_html_uses_truncated_text(self):
        long_text = 'Please ' + ('make this very detailed ' * 10)
        html = _custom_style_comment_html({'text': long_text}, lang='en')
        self.assertIn('Comment:', html)
        self.assertIn('…', html)

    def test_generate_pdf_with_custom_style_comment(self):
        item = self.order.order_items.first()
        item.custom_styles = [{
            'style_type': 'collar',
            'label': 'Classic Collar',
            'asset_path': 'custom_styles/missing.png',
            'text': 'Keep collar firm',
        }]
        item.save(update_fields=['custom_styles'])

        pdf_bytes = generate_order_pdf(self.order, lang='en')
        self.assertTrue(pdf_bytes.startswith(b'%PDF'))
        self.assertGreater(len(pdf_bytes), 1000)

    @override_settings(MEDIA_ROOT='/tmp/zthob-style-ref-pdf-test')
    def test_resolve_media_file_path_supports_api_media_urls(self):
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as media_root:
            rel_path = 'style_references/2026/07/sample.png'
            full_path = os.path.join(media_root, rel_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'wb') as handle:
                handle.write(b'png')

            with self.settings(MEDIA_ROOT=media_root):
                self.assertEqual(
                    _resolve_media_file_path(rel_path),
                    full_path,
                )
                self.assertEqual(
                    _resolve_media_file_path(f'https://prod.mgask.net/api/media/{rel_path}'),
                    full_path,
                )
                paths = _style_reference_image_paths({
                    'reference_images': [
                        rel_path,
                        f'https://prod.mgask.net/api/media/{rel_path}',
                    ],
                })
                self.assertEqual(paths, [full_path, full_path])

    @override_settings(MEDIA_ROOT='/tmp/zthob-style-ref-pdf-test')
    def test_generate_pdf_with_reference_images(self):
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as media_root:
            rel_path = 'style_references/2026/07/reference.png'
            full_path = os.path.join(media_root, rel_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'wb') as handle:
                handle.write(
                    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
                    b'\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
                    b'\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01'
                    b'\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
                )

            item = self.order.order_items.first()
            item.custom_styles = [{
                'style_type': 'collar',
                'label': 'Classic Collar',
                'asset_path': rel_path,
                'text': 'Match this photo',
                'reference_images': [rel_path],
            }]
            item.save(update_fields=['custom_styles'])

            with self.settings(MEDIA_ROOT=media_root):
                pdf_bytes = generate_order_pdf(self.order, lang='en')

            self.assertTrue(pdf_bytes.startswith(b'%PDF'))
            self.assertGreater(len(pdf_bytes), 1000)
