from django.test import SimpleTestCase

from apps.core.phone_format import (
    normalize_phone_to_local,
    phone_lookup_variations,
)


class PhoneLookupVariationsTest(SimpleTestCase):
    def test_variations_for_international_number(self):
        variations = phone_lookup_variations('+966539227332')
        self.assertIn('0539227332', variations)
        self.assertIn('+966539227332', variations)
        self.assertIn('966539227332', variations)
        self.assertIn('539227332', variations)

    def test_normalize_specific_client_number(self):
        self.assertEqual(normalize_phone_to_local('+966539227332'), '0539227332')
