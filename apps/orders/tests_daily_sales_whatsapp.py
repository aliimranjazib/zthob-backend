from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, override_settings
from apps.accounts.models import CustomUser
from apps.orders.daily_sales_whatsapp import (
    SalesSlice,
    build_daily_sales_parameters,
    run_daily_sales_whatsapp_job,
    send_daily_sales_report_for_shop,
    utc_bounds_for_local_date,
)
from apps.orders.models import DailySalesWhatsAppDelivery, Order, OrderStatusHistory
from apps.tailors.models import TailorProfile


@override_settings(
    WSLA_WHATSAPP_ENABLED=True,
    WSLA_WHATSAPP_TOKEN='test-token',
    WSLA_DAILY_SALES_REPORT_ENABLED=True,
    WSLA_TEMPLATE_DAILY_SALES_REPORT='mgask_daily_sales_report',
    WSLA_DAILY_SALES_INCLUDE_PLATFORM_IN_LINE9=True,
)
class DailySalesWhatsAppTests(TestCase):
    def setUp(self):
        self.owner = CustomUser.objects.create_user(
            username='owner_daily',
            phone='0504444444',
            password='pass12345',
            role='TAILOR',
        )
        self.customer = CustomUser.objects.create_user(
            username='cust_daily',
            phone='0505555555',
            password='pass12345',
            role='USER',
        )
        self.shop = TailorProfile.objects.create(
            owner=self.owner,
            shop_name='Peace Tailors',
            contact_number='0506666666',
            shop_status=True,
        )
        self.order = Order.objects.create(
            customer=self.customer,
            tailor=self.owner,
            shop=self.shop,
            service_mode='walk_in',
            order_type='fabric_with_stitching',
            payment_status='paid',
            status='collected',
            total_amount=Decimal('100.00'),
            order_number='MG-DAILY-1',
        )

    def test_build_nine_parameters(self):
        report = date(2026, 11, 10)
        empty = SalesSlice(0, Decimal('0'))
        params = build_daily_sales_parameters(
            report_date=report,
            shop_name='Peace Tailors',
            home=SalesSlice(10, Decimal('270')),
            walk=SalesSlice(4, Decimal('100')),
            total=SalesSlice(14, Decimal('370')),
            platform_home=empty,
            platform_walk=empty,
            platform_total=empty,
        )
        self.assertEqual(len(params), 9)
        self.assertEqual(params[0], '2026-11-10')
        self.assertEqual(params[1], 'Peace Tailors')
        self.assertEqual(params[2], '10')
        self.assertEqual(params[4], '4')
        self.assertEqual(params[6], '14')
        self.assertEqual(params[7], '370.00')
        self.assertIn('المنصة', params[8])

    @patch('apps.orders.daily_sales_whatsapp.WslaWhatsAppService.send_template')
    def test_send_idempotent(self, mock_send):
        mock_send.return_value = (True, 'ok', 'wamid.daily')
        report = date(2026, 11, 10)
        start, end = utc_bounds_for_local_date(report)
        OrderStatusHistory.objects.create(
            order=self.order,
            status='collected',
            previous_status='ready_for_pickup',
            created_at=start,
        )
        empty = SalesSlice(0, Decimal('0'))
        self.assertTrue(
            send_daily_sales_report_for_shop(
                self.shop,
                report_date=report,
                start_utc=start,
                end_utc=end,
                platform_home=empty,
                platform_walk=SalesSlice(1, Decimal('100')),
                platform_total=SalesSlice(1, Decimal('100')),
            )
        )
        self.assertTrue(
            send_daily_sales_report_for_shop(
                self.shop,
                report_date=report,
                start_utc=start,
                end_utc=end,
                platform_home=empty,
                platform_walk=SalesSlice(1, Decimal('100')),
                platform_total=SalesSlice(1, Decimal('100')),
            )
        )
        self.assertEqual(mock_send.call_count, 1)
        self.assertEqual(
            DailySalesWhatsAppDelivery.objects.filter(
                report_key=f'shop:{self.shop.id}:2026-11-10',
                status=DailySalesWhatsAppDelivery.STATUS_SENT,
            ).count(),
            1,
        )

    @patch('apps.orders.daily_sales_whatsapp.WslaWhatsAppService.send_template')
    def test_job_counts_shop(self, mock_send):
        mock_send.return_value = (True, 'ok', 'wamid.daily')
        report = date(2026, 11, 10)
        start, _ = utc_bounds_for_local_date(report)
        OrderStatusHistory.objects.create(
            order=self.order,
            status='collected',
            previous_status='ready_for_pickup',
            created_at=start,
        )
        stats = run_daily_sales_whatsapp_job(report_date=report)
        self.assertGreaterEqual(stats['sent'], 1)
