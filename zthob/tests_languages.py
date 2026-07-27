from django.test import SimpleTestCase

from zthob.languages import is_rtl_language, taqnyat_sms_language


class LanguageHelperTests(SimpleTestCase):
    def test_is_rtl_language(self):
        self.assertTrue(is_rtl_language('ar'))
        self.assertTrue(is_rtl_language('ur'))
        self.assertFalse(is_rtl_language('en'))

    def test_taqnyat_sms_language_maps_urdu_to_english(self):
        self.assertEqual(taqnyat_sms_language('ur'), 'en')
        self.assertEqual(taqnyat_sms_language('en'), 'en')
        self.assertEqual(taqnyat_sms_language('ar'), 'ar')
        self.assertEqual(taqnyat_sms_language(None), 'ar')
