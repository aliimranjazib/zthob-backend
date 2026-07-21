from django.test import TestCase

from apps.customization.models import CustomStyle, CustomStyleCategory
from apps.orders.serializers import OrderItemCreateSerializer, OrderUpdateSerializer


class CustomStyleTextSerializerTest(TestCase):
    def setUp(self):
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

    def test_order_level_custom_style_preserves_frontend_text(self):
        serializer = OrderUpdateSerializer()

        styles = serializer.validate_custom_styles([
            {
                'category': 'cuff',
                'style_id': self.style.id,
                'text': 'Use contrast stitching',
            }
        ])

        self.assertEqual(styles, [{
            'style_id': self.style.id,
            'style_type': 'cuff',
            'index': 2,
            'label': 'Rounded Cuff',
            'asset_path': 'custom_styles/rounded_cuff.png',
            'text': 'Use contrast stitching',
        }])

    def test_item_level_custom_style_preserves_frontend_text(self):
        serializer = OrderItemCreateSerializer()

        styles = serializer.validate_custom_styles([
            {
                'category': 'cuff',
                'style_id': self.style.id,
                'text': 'Make this slightly loose',
            }
        ])

        self.assertEqual(styles[0]['text'], 'Make this slightly loose')
        self.assertEqual(styles[0]['style_type'], 'cuff')
