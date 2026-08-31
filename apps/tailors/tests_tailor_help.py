from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from apps.tailors.content.tailor_faq import get_tailor_faq_content, resolve_faq_language


class TailorFaqContentTest(SimpleTestCase):
    def test_resolve_language_defaults_to_arabic(self):
        self.assertEqual(resolve_faq_language(None), 'ar')
        self.assertEqual(resolve_faq_language('invalid'), 'ar')

    def test_supported_languages_return_content(self):
        for lang in ('en', 'ar', 'ur'):
            content = get_tailor_faq_content(lang)
            self.assertTrue(content['heading'])
            self.assertGreater(len(content['categories']), 0)


class TailorHelpPageTest(TestCase):
    def test_tailor_help_page_renders(self):
        response = self.client.get(reverse('tailor-help'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Help &amp; FAQs')

    def test_tailor_help_page_arabic(self):
        response = self.client.get(reverse('tailor-help'), {'lang': 'ar'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'المساعدة والأسئلة الشائعة')
        self.assertContains(response, 'dir="rtl"')

    def test_tailor_help_page_urdu(self):
        response = self.client.get(reverse('tailor-help'), {'lang': 'ur'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'مدد اور عمومی سوالات')
