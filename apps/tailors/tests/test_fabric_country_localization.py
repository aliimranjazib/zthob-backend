from django.test import RequestFactory, TestCase

from apps.tailors.models import FabricCountry
from apps.tailors.serializers.catalog import FabricCountrySerializer


class FabricCountryLocalizationTests(TestCase):
    def setUp(self):
        self.country = FabricCountry.objects.create(
            code="XX",
            name="Testland",
            name_ar="أرض الاختبار",
            name_ur="ٹیسٹ لینڈ",
            description="English description",
            description_ar="وصف عربي",
            description_ur="اردو تفصیل",
            display_order=99,
            is_active=True,
        )
        self.factory = RequestFactory()

    def _serialize(self, language):
        request = self.factory.get(
            "/api/tailors/fabric-countries/",
            HTTP_ACCEPT_LANGUAGE=language,
        )
        data = FabricCountrySerializer(
            self.country, context={"request": request}
        ).data
        return data

    def test_localized_fields_follow_accept_language_en(self):
        data = self._serialize("en")
        self.assertEqual(data["localized_name"], "Testland")
        self.assertEqual(data["localized_description"], "English description")
        self.assertEqual(data["name_ur"], "ٹیسٹ لینڈ")

    def test_localized_fields_follow_accept_language_ar(self):
        data = self._serialize("ar")
        self.assertEqual(data["localized_name"], "أرض الاختبار")
        self.assertEqual(data["localized_description"], "وصف عربي")

    def test_localized_fields_follow_accept_language_ur(self):
        data = self._serialize("ur")
        self.assertEqual(data["localized_name"], "ٹیسٹ لینڈ")
        self.assertEqual(data["localized_description"], "اردو تفصیل")

    def test_model_fallback_when_ur_missing(self):
        self.country.description_ur = ""
        self.country.save(update_fields=["description_ur"])
        self.assertEqual(
            self.country.get_localized_description("ur"),
            "وصف عربي",
        )
