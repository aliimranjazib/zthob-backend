from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient, APIRequestFactory

from apps.customization.models import CustomStyle, CustomStyleCategory
from apps.orders.models import StyleReferenceImage
from apps.orders.serializers import OrderUpdateSerializer, format_custom_styles_for_response
from apps.orders.style_references import MAX_STYLE_REFERENCE_IMAGES
from apps.tailors.models import Fabric, FabricCategory, TailorProfile


User = get_user_model()

TEST_PNG_BYTES = (
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
    b'\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
    b'\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01'
    b'\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
)


def make_test_png(name='reference.png'):
    return SimpleUploadedFile(name, TEST_PNG_BYTES, content_type='image/png')


TEST_PNG = make_test_png()


def upload_style_reference(client):
    response = client.post(
        '/api/orders/style-reference/upload/',
        {'image': make_test_png()},
        format='multipart',
    )
    assert response.status_code == 201, response.data
    return response.data['data']


@override_settings(
    SECURE_SSL_REDIRECT=False,
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    },
)
class StyleReferenceUploadAPITest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='style_ref_user',
            password='testpass123',
            role='USER',
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_upload_returns_id_path_and_url(self):
        data = upload_style_reference(self.client)
        self.assertIn('id', data)
        self.assertTrue(data['path'].startswith('style_references/'))
        self.assertIn('/api/media/style_references/', data['url'])

    def test_upload_requires_authentication(self):
        client = APIClient()
        response = client.post(
            '/api/orders/style-reference/upload/',
            {'image': TEST_PNG},
            format='multipart',
        )
        self.assertEqual(response.status_code, 401)

    def test_upload_rejects_invalid_file_type(self):
        bad_file = SimpleUploadedFile('reference.txt', b'not-an-image', content_type='text/plain')
        response = self.client.post(
            '/api/orders/style-reference/upload/',
            {'image': bad_file},
            format='multipart',
        )
        self.assertEqual(response.status_code, 400)


class StyleReferenceOrderSerializerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='style_ref_customer',
            password='testpass123',
            role='USER',
        )
        self.other_user = User.objects.create_user(
            username='style_ref_other',
            password='testpass123',
            role='USER',
        )
        self.category = CustomStyleCategory.objects.create(
            name='cuff',
            display_name='Cuff Styles',
            display_order=1,
            is_active=True,
        )
        self.style = CustomStyle.objects.create(
            category=self.category,
            name='Rounded Cuff',
            code='rounded_cuff',
            image='custom_styles/rounded_cuff.png',
            display_order=2,
            is_active=True,
        )
        self.owned_images = [
            StyleReferenceImage.objects.create(image=make_test_png(f'reference_{index}.png'), uploaded_by=self.user)
            for index in range(2)
        ]
        self.foreign_image = StyleReferenceImage.objects.create(
            image=make_test_png('foreign.png'),
            uploaded_by=self.other_user,
        )
        self.factory = APIRequestFactory()

    def _serializer(self):
        request = self.factory.get('/')
        request.user = self.user
        return OrderUpdateSerializer(context={'request': request})

    def test_order_custom_styles_preserve_multiple_reference_images(self):
        styles = self._serializer().validate_custom_styles([
            {
                'style_id': self.style.id,
                'text': 'Use these photos',
                'reference_image_ids': [img.id for img in self.owned_images],
            }
        ])

        self.assertEqual(len(styles[0]['reference_images']), 2)
        self.assertTrue(all(path.startswith('style_references/') for path in styles[0]['reference_images']))
        self.assertEqual(styles[0]['text'], 'Use these photos')

    def test_rejects_foreign_reference_image_ids(self):
        serializer = self._serializer()
        with self.assertRaises(Exception):
            serializer.validate_custom_styles([
                {
                    'style_id': self.style.id,
                    'reference_image_ids': [self.foreign_image.id],
                }
            ])

    def test_rejects_more_than_four_reference_images(self):
        image_ids = []
        for _ in range(MAX_STYLE_REFERENCE_IMAGES + 1):
            image_ids.append(
                StyleReferenceImage.objects.create(
                    image=make_test_png(f'limit_{_}.png'),
                    uploaded_by=self.user,
                ).id
            )

        serializer = self._serializer()
        with self.assertRaises(Exception):
            serializer.validate_custom_styles([
                {
                    'style_id': self.style.id,
                    'reference_image_ids': image_ids,
                }
            ])

    def test_response_includes_reference_image_urls(self):
        request = self.factory.get('/')
        request.META['HTTP_HOST'] = 'prod.mgask.net'
        request.META['wsgi.url_scheme'] = 'https'

        styles = [{
            'style_id': self.style.id,
            'style_type': 'cuff',
            'label': 'Rounded Cuff',
            'asset_path': 'custom_styles/rounded_cuff.png',
            'reference_images': [img.image.name for img in self.owned_images],
        }]
        formatted = format_custom_styles_for_response(styles, request)
        self.assertEqual(len(formatted[0]['reference_images']), 2)
        self.assertTrue(formatted[0]['reference_images'][0].startswith('https://prod.mgask.net/api/media/'))

    def test_response_resolves_legacy_reference_image_ids(self):
        request = self.factory.get('/')
        request.META['HTTP_HOST'] = 'prod.mgask.net'
        request.META['wsgi.url_scheme'] = 'https'

        styles = [{
            'style_id': self.style.id,
            'style_type': 'cuff',
            'label': 'Rounded Cuff',
            'asset_path': 'custom_styles/rounded_cuff.png',
            'reference_image_ids': [self.owned_images[0].id],
        }]
        formatted = format_custom_styles_for_response(styles, request)
        self.assertEqual(len(formatted[0]['reference_images']), 1)
        self.assertIn('/api/media/style_references/', formatted[0]['reference_images'][0])
        self.assertNotIn('reference_image_ids', formatted[0])

    def test_response_always_includes_reference_images_key(self):
        request = self.factory.get('/')
        styles = [{
            'style_id': self.style.id,
            'style_type': 'cuff',
            'label': 'Rounded Cuff',
            'asset_path': 'custom_styles/rounded_cuff.png',
        }]
        formatted = format_custom_styles_for_response(styles, request)
        self.assertIn('reference_images', formatted[0])
        self.assertEqual(formatted[0]['reference_images'], [])


@override_settings(
    SECURE_SSL_REDIRECT=False,
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    },
)
class StyleReferenceOrderCreateAPITest(TestCase):
    def setUp(self):
        cache.clear()
        self.customer = User.objects.create_user(
            username='style_ref_order_customer',
            password='testpass123',
            role='USER',
        )
        self.tailor_user = User.objects.create_user(
            username='style_ref_order_tailor',
            password='testpass123',
            role='TAILOR',
        )
        self.tailor_profile, _ = TailorProfile.objects.get_or_create(
            user=self.tailor_user,
            defaults={'shop_name': 'Style Ref Shop', 'shop_status': True},
        )
        self.fabric_category = FabricCategory.objects.create(name='Fabric', slug='fabric')
        self.fabric = Fabric.objects.create(
            tailor=self.tailor_profile,
            name='Style Fabric',
            price=Decimal('100.00'),
            stock=10,
            is_active=True,
            category=self.fabric_category,
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
        self.client = APIClient()
        self.client.force_authenticate(user=self.customer)

    def test_create_order_with_reference_images_on_item(self):
        uploaded = upload_style_reference(self.client)

        response = self.client.post(
            '/api/orders/create/',
            {
                'customer': self.customer.id,
                'tailor': self.tailor_user.id,
                'order_type': 'fabric_with_stitching',
                'service_mode': 'walk_in',
                'payment_method': 'cod',
                'stitching_price': '150.00',
                'items': [{
                    'fabric': self.fabric.id,
                    'quantity': 1,
                    'custom_styles': [{
                        'style_id': self.style.id,
                        'text': 'Like this collar photo',
                        'reference_image_ids': [uploaded['id']],
                    }],
                }],
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201, response.data)
        item_styles = response.data['data']['items'][0]['custom_styles']
        self.assertEqual(len(item_styles[0]['reference_images']), 1)
        self.assertIn('/api/media/style_references/', item_styles[0]['reference_images'][0])
