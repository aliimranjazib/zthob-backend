from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.customization.models import CustomStyle, CustomStyleCategory
from apps.orders.models import Order, OrderItem


User = get_user_model()


@override_settings(
    SECURE_SSL_REDIRECT=False,
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }
)
class RiderStyleUpdateAPITest(TestCase):
    def setUp(self):
        cache.clear()
        self.customer = User.objects.create_user(
            username='style_customer',
            password='testpass123',
            role='USER',
        )
        self.rider = User.objects.create_user(
            username='style_rider',
            password='testpass123',
            role='RIDER',
        )
        self.tailor = User.objects.create_user(
            username='style_tailor',
            password='testpass123',
            role='TAILOR',
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
        self.order = Order.objects.create(
            customer=self.customer,
            tailor=self.tailor,
            rider=self.rider,
            assigned_rider=self.rider,
            order_type='fabric_with_stitching',
            service_mode='home_delivery',
            status='confirmed',
            rider_status='accepted',
            payment_status='paid',
            total_amount=Decimal('100.00'),
            paid_amount=Decimal('100.00'),
            remaining_amount=Decimal('0.00'),
        )
        self.item = OrderItem.objects.create(
            order=self.order,
            fabric=None,
            quantity=1,
            unit_price=Decimal('100.00'),
            total_price=Decimal('100.00'),
            measurements={'length': '145'},
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.rider)

    def test_request_style_consent_sends_code_to_customer(self):
        with patch('apps.riders.views.base.NotificationService.send_notification', return_value=True) as mock_send:
            response = self.client.post(
                f'/api/riders/orders/{self.order.id}/request-style-consent/',
                data={},
                format='json',
            )

        self.assertEqual(response.status_code, 200)
        code = cache.get(f'style_consent_{self.order.id}')
        self.assertRegex(code, r'^\d{4}$')
        mock_send.assert_called_once()
        self.assertEqual(mock_send.call_args.kwargs['user'], self.customer)
        self.assertEqual(mock_send.call_args.kwargs['notification_type'], 'STYLE_CONSENT')

    def test_assigned_rider_can_request_style_consent_before_rider_field_sync(self):
        self.order.rider = None
        self.order.assigned_rider = self.rider
        self.order.save(update_fields=['rider', 'assigned_rider', 'updated_at'])

        with patch('apps.riders.views.base.NotificationService.send_notification', return_value=True):
            response = self.client.post(
                f'/api/riders/orders/{self.order.id}/request-style-consent/',
                data={},
                format='json',
            )

        self.assertEqual(response.status_code, 200)
        self.assertRegex(cache.get(f'style_consent_{self.order.id}'), r'^\d{4}$')

    def test_update_style_with_valid_consent_updates_order_and_items(self):
        cache.set(f'style_consent_{self.order.id}', '1234', timeout=600)

        response = self.client.post(
            f'/api/riders/orders/{self.order.id}/update-style/',
            data={
                'consent_code': '1234',
                'save_as_default': True,
                'styles': [
                    {'category': 'collar', 'style_id': self.style.id, 'text': 'Customer wants a soft collar'},
                ],
            },
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.item.refresh_from_db()
        expected_style = {
            'style_type': 'collar',
            'index': 3,
            'label': 'Classic Collar',
            'asset_path': 'custom_styles/classic_collar.png',
            'text': 'Customer wants a soft collar',
        }
        self.assertEqual(self.order.custom_styles, [expected_style])
        self.assertEqual(self.item.custom_styles, [expected_style])
        self.assertIsNone(cache.get(f'style_consent_{self.order.id}'))
        preset = self.customer.style_presets.get(name='My Style (Updated by Rider)')
        self.assertTrue(preset.is_default)
        self.assertEqual(
            preset.styles,
            [{'category': 'collar', 'style_id': self.style.id, 'text': 'Customer wants a soft collar'}]
        )

    def test_update_style_with_reference_images(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from apps.orders.models import StyleReferenceImage

        test_png = SimpleUploadedFile(
            'reference.png',
            (
                b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
                b'\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
                b'\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01'
                b'\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
            ),
            content_type='image/png',
        )
        image_one = StyleReferenceImage.objects.create(image=test_png, uploaded_by=self.rider)
        image_two = StyleReferenceImage.objects.create(image=test_png, uploaded_by=self.rider)
        cache.set(f'style_consent_{self.order.id}', '1234', timeout=600)

        response = self.client.post(
            f'/api/riders/orders/{self.order.id}/update-style/',
            data={
                'consent_code': '1234',
                'styles': [{
                    'category': 'collar',
                    'style_id': self.style.id,
                    'text': 'Use these photos',
                    'reference_image_ids': [image_one.id, image_two.id],
                }],
            },
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.item.refresh_from_db()
        self.assertEqual(len(self.item.custom_styles[0]['reference_images']), 2)
        self.assertTrue(
            all(path.startswith('style_references/') for path in self.item.custom_styles[0]['reference_images'])
        )

    def test_update_style_rejects_invalid_consent_code(self):
        cache.set(f'style_consent_{self.order.id}', '1234', timeout=600)

        response = self.client.post(
            f'/api/riders/orders/{self.order.id}/update-style/',
            data={
                'consent_code': '9999',
                'styles': [
                    {'category': 'collar', 'style_id': self.style.id},
                ],
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.item.refresh_from_db()
        self.assertIsNone(self.item.custom_styles)

    def test_assigned_rider_can_update_style_even_before_rider_field_sync(self):
        self.order.rider = None
        self.order.assigned_rider = self.rider
        self.order.save(update_fields=['rider', 'assigned_rider', 'updated_at'])
        cache.set(f'style_consent_{self.order.id}', '1234', timeout=600)

        response = self.client.post(
            f'/api/riders/orders/{self.order.id}/update-style/',
            data={
                'consent_code': '1234',
                'styles': [
                    {'category': 'collar', 'style_id': self.style.id},
                ],
            },
            format='json',
        )

        self.assertEqual(response.status_code, 200)
