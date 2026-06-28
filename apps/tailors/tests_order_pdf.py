from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.customers.models import CustomerProfile, FamilyMember
from apps.orders.models import Order, OrderItem
from apps.tailors.models import Fabric, FabricCategory, TailorProfile
from apps.tailors.services.order_pdf import (
    _ARABIC_FONT_AVAILABLE,
    _contains_arabic,
    _custom_style_caption_html,
    _format_recipient_html,
    _format_user_text_html,
    _item_recipient_display,
    _t,
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
        from apps.tailors.services.order_pdf import _shape_arabic, _t
        once = _t('Fabric + Stitching', lang='ar')
        html = _format_user_text_html(once, lang='ar', reshape=False)
        self.assertIn('IBMPlexSansArabic-Regular', html)
        twice = _shape_arabic(_shape_arabic('قماش مع خياطة'))
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
        self.assertIn(_t('Comment', 'ar'), html)

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
