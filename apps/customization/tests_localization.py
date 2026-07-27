from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.customization.models import MeasurementField, MeasurementTemplate

User = get_user_model()


class MeasurementLocalizationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='measurement_user',
            password='testpass123',
        )
        self.client.force_authenticate(user=self.user)
        self.template = MeasurementTemplate.objects.create(
            name='thobe',
            display_name='Thobe',
            display_name_ar='ثوب',
            display_name_ur='قمیض',
        )
        self.field = MeasurementField.objects.create(
            template=self.template,
            name='chest',
            display_name='Chest',
            display_name_ar='الصدر',
            display_name_ur='سینہ',
            help_text_en='Measure around chest',
            help_text_ar='قم بالقياس حول الصدر',
            help_text_ur='سینے کے گرد ناپ لیں',
        )
        self.url = '/api/customization/measurement-templates/'

    def test_measurement_template_returns_urdu_labels(self):
        response = self.client.get(self.url, HTTP_ACCEPT_LANGUAGE='ur')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        templates = response.data
        if isinstance(templates, dict):
            templates = templates['data']
        template_data = templates[0]
        self.assertEqual(template_data['display_name'], 'قمیض')
        field_data = template_data['measurement_fields'][0]
        self.assertEqual(field_data['display_name'], 'سینہ')
        self.assertEqual(field_data['help_text'], 'سینے کے گرد ناپ لیں')
