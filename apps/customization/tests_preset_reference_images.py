from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIRequestFactory, APIClient

from apps.customization.models import CustomStyle, CustomStyleCategory, UserStylePreset
from apps.customization.serializers import UserStylePresetSerializer
from apps.orders.models import StyleReferenceImage


User = get_user_model()

TEST_PNG_BYTES = (
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
    b'\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
    b'\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01'
    b'\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
)


@override_settings(SECURE_SSL_REDIRECT=False)
class StylePresetReferenceImagesTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='preset_ref_user',
            password='testpass123',
            role='USER',
        )
        self.category = CustomStyleCategory.objects.create(
            name='collar',
            display_name='Collar Styles',
            display_order=1,
            is_active=True,
        )
        self.style = CustomStyle.objects.create(
            category=self.category,
            name='Classic Collar',
            code='classic_collar',
            image='custom_styles/classic_collar.png',
            display_order=3,
            is_active=True,
        )
        self.image = StyleReferenceImage.objects.create(
            image=SimpleUploadedFile('reference.png', TEST_PNG_BYTES, content_type='image/png'),
            uploaded_by=self.user,
        )
        self.factory = APIRequestFactory()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def _request(self):
        request = self.factory.get('/')
        request.META['HTTP_HOST'] = 'app.mgask.net'
        request.META['wsgi.url_scheme'] = 'https'
        request.user = self.user
        return request

    def test_preset_response_includes_reference_image_urls(self):
        preset = UserStylePreset.objects.create(
            user=self.user,
            name='My Style',
            styles=[{
                'category': 'collar',
                'style_id': self.style.id,
                'text': 'Like this photo',
                'reference_images': [self.image.image.name],
            }],
        )

        data = UserStylePresetSerializer(preset, context={'request': self._request()}).data

        self.assertIn('/api/media/style_references/', data['styles'][0]['reference_images'][0])
        self.assertIn('/api/media/style_references/', data['styles_details'][0]['reference_images'][0])
        self.assertEqual(data['styles'][0]['text'], 'Like this photo')

    def test_preset_create_accepts_reference_image_ids(self):
        response = self.client.post(
            '/api/customization/presets/',
            {
                'name': 'Saved Style',
                'styles': [{
                    'category': 'collar',
                    'style_id': self.style.id,
                    'text': 'Use these',
                    'reference_image_ids': [self.image.id],
                }],
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201, response.data)
        preset = UserStylePreset.objects.get(name='Saved Style')
        self.assertTrue(preset.styles[0]['reference_images'][0].startswith('style_references/'))
        self.assertNotIn('reference_image_ids', preset.styles[0])
        self.assertIn('/api/media/style_references/', response.data['styles'][0]['reference_images'][0])

    def test_legacy_preset_reference_image_ids_are_resolved_on_read(self):
        preset = UserStylePreset.objects.create(
            user=self.user,
            name='Legacy Style',
            styles=[{
                'category': 'collar',
                'style_id': self.style.id,
                'reference_image_ids': [self.image.id],
            }],
        )

        data = UserStylePresetSerializer(preset, context={'request': self._request()}).data

        self.assertEqual(len(data['styles'][0]['reference_images']), 1)
        self.assertIn('/api/media/style_references/', data['styles'][0]['reference_images'][0])
