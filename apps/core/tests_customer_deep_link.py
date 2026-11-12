import json
from decimal import Decimal
from unittest.mock import patch

from django.test import Client, TestCase, override_settings

from apps.accounts.models import CustomUser
from apps.core.wsla_whatsapp_service import WslaWhatsAppService
from apps.orders.models import Order
from apps.orders.walk_in_whatsapp import EVENT_ORDER_CREATED, send_walk_in_whatsapp
from apps.tailors.models import TailorProfile


class CustomerDeepLinkParserTests(TestCase):
    def test_parse_order_id(self):
        from apps.core.customer_deep_link import parse_order_id_from_path

        self.assertEqual(parse_order_id_from_path('4521'), 4521)
        self.assertIsNone(parse_order_id_from_path('0'))
        self.assertIsNone(parse_order_id_from_path('-1'))
        self.assertIsNone(parse_order_id_from_path('abc'))
        self.assertIsNone(parse_order_id_from_path(''))
        self.assertIsNone(parse_order_id_from_path('01'))


class CustomerDeepLinkHttpTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_invalid_order_id_404(self):
        response = self.client.get('/order/not-a-number')
        self.assertEqual(response.status_code, 404)

    def test_valid_order_id_landing(self):
        response = self.client.get('/order/42')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Mgask', response.content)

    @override_settings(
        CUSTOMER_APP_ANDROID_SHA256_FINGERPRINTS='AB' * 32,
        CUSTOMER_APP_ANDROID_PACKAGE='com.mgask.customerapp',
    )
    def test_assetlinks_json(self):
        response = self.client.get('/.well-known/assetlinks.json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['target']['package_name'], 'com.mgask.customerapp')

    @override_settings(
        CUSTOMER_APP_APPLE_TEAM_ID='TEAM123',
        CUSTOMER_APP_IOS_BUNDLE_ID='com.mgask.customerapp',
    )
    def test_apple_app_site_association(self):
        response = self.client.get('/.well-known/apple-app-site-association')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['applinks']['details'][0]['appID'], 'TEAM123.com.mgask.customerapp')
        self.assertEqual(data['applinks']['details'][0]['paths'], ['/order/*'])


class WslaUrlButtonTests(TestCase):
    @patch('apps.core.wsla_whatsapp_service.urllib.request.urlopen')
    @override_settings(
        WSLA_WHATSAPP_ENABLED=True,
        WSLA_WHATSAPP_TOKEN='token',
    )
    def test_send_template_includes_url_button(self, mock_urlopen):
        mock_response = mock_urlopen.return_value.__enter__.return_value
        mock_response.read.return_value = b'{"status":"accepted","messageId":"1"}'

        WslaWhatsAppService.send_template(
            phone_number='966555532161',
            template_name='mgask_walk_in_order_created',
            language='ar',
            body_parameters=['a'] * 7,
            url_button_suffix='4521',
        )

        request = mock_urlopen.call_args[0][0]
        payload = json.loads(request.data.decode('utf-8'))
        self.assertEqual(len(payload['components']), 2)
        button = payload['components'][1]
        self.assertEqual(button['type'], 'button')
        self.assertEqual(button['sub_type'], 'url')
        self.assertEqual(button['parameters'][0]['text'], '4521')


@override_settings(
    WSLA_WHATSAPP_ENABLED=True,
    WSLA_WHATSAPP_TOKEN='test-token',
    WSLA_TEMPLATE_WALK_IN_CREATED='mgask_walk_in_order_created',
    CUSTOMER_ORDER_DEEP_LINK_BASE='https://prod.mgask.net/order/',
    WSLA_WALK_IN_ORDER_URL_BUTTON_ENABLED=True,
)
class WalkInWhatsAppUrlButtonTests(TestCase):
    def setUp(self):
        self.owner = CustomUser.objects.create_user(
            username='owner2',
            phone='0501111112',
            password='pass12345',
            role='TAILOR',
        )
        self.customer = CustomUser.objects.create_user(
            username='cust2',
            phone='0502222223',
            password='pass12345',
            role='USER',
        )
        self.shop = TailorProfile.objects.create(
            owner=self.owner,
            user=None,
            shop_name='Shop',
            contact_number='0503333334',
            address='Addr',
        )
        self.order = Order.objects.create(
            customer=self.customer,
            tailor=self.owner,
            shop=self.shop,
            service_mode='walk_in',
            order_type='fabric_with_stitching',
            payment_status='paid',
            status='confirmed',
            tailor_status='accepted',
            total_amount=Decimal('50.00'),
            order_number='MG-2',
        )

    @patch('apps.orders.walk_in_whatsapp.WslaWhatsAppService.send_template')
    def test_walk_in_passes_order_id_as_url_suffix(self, mock_send):
        mock_send.return_value = (True, 'ok', 'wamid')
        send_walk_in_whatsapp(self.order.id, EVENT_ORDER_CREATED)
        kwargs = mock_send.call_args.kwargs
        self.assertEqual(kwargs['url_button_suffix'], str(self.order.id))
        self.assertEqual(len(kwargs['body_parameters']), 7)

    @override_settings(WSLA_WALK_IN_ORDER_URL_BUTTON_ENABLED=False)
    @patch('apps.orders.walk_in_whatsapp.WslaWhatsAppService.send_template')
    def test_walk_in_skips_button_when_disabled(self, mock_send):
        mock_send.return_value = (True, 'ok', 'wamid')
        send_walk_in_whatsapp(self.order.id, EVENT_ORDER_CREATED)
        self.assertIsNone(mock_send.call_args.kwargs.get('url_button_suffix'))
