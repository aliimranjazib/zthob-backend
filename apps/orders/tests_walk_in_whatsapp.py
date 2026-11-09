from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, override_settings

from apps.accounts.models import CustomUser
from apps.orders.models import Order, WalkInWhatsAppDelivery
from apps.orders.walk_in_whatsapp import (
    EVENT_ORDER_CREATED,
    build_order_created_parameters,
    build_ready_for_pickup_parameters,
    send_walk_in_whatsapp,
)
from apps.tailors.models import TailorProfile


@override_settings(
    WSLA_WHATSAPP_ENABLED=True,
    WSLA_WHATSAPP_TOKEN='test-token',
    WSLA_TEMPLATE_WALK_IN_CREATED='mgask_walk_in_order_created',
    WSLA_TEMPLATE_WALK_IN_READY='mgask_walk_in_ready',
)
class WalkInWhatsAppTests(TestCase):
    def setUp(self):
        self.owner = CustomUser.objects.create_user(
            username='owner1',
            phone='0501111111',
            password='pass12345',
            role='TAILOR',
        )
        self.customer = CustomUser.objects.create_user(
            username='cust1',
            phone='0502222222',
            password='pass12345',
            role='USER',
        )
        self.shop = TailorProfile.objects.create(
            owner=self.owner,
            user=None,
            shop_name='Test Shop',
            contact_number='0503333333',
            address='Riyadh Test Street',
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
            total_amount=Decimal('100.00'),
            order_number='MG-TEST-1',
        )

    def test_build_order_created_parameters_order(self):
        params = build_order_created_parameters(self.order)
        self.assertEqual(len(params), 7)
        self.assertEqual(params[2], 'MG-TEST-1')
        self.assertEqual(params[6], 'Riyadh Test Street')

    def test_build_ready_parameters(self):
        self.order.status = 'ready_for_pickup'
        params = build_ready_for_pickup_parameters(self.order)
        self.assertEqual(len(params), 5)
        self.assertEqual(params[1], 'MG-TEST-1')

    @patch('apps.orders.walk_in_whatsapp.WslaWhatsAppService.send_template')
    def test_send_order_created_idempotent(self, mock_send):
        mock_send.return_value = (True, 'ok', 'wamid.123')
        self.assertTrue(send_walk_in_whatsapp(self.order.id, EVENT_ORDER_CREATED))
        self.assertTrue(send_walk_in_whatsapp(self.order.id, EVENT_ORDER_CREATED))
        self.assertEqual(mock_send.call_count, 1)
        self.assertEqual(
            WalkInWhatsAppDelivery.objects.filter(
                order=self.order,
                event=EVENT_ORDER_CREATED,
                status=WalkInWhatsAppDelivery.STATUS_SENT,
            ).count(),
            1,
        )
