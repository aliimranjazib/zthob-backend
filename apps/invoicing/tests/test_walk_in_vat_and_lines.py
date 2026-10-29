from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from apps.invoicing.line_builder import build_zatca_lines_for_order
from apps.invoicing.services.walk_in_invoice import issue_walk_in_tax_invoice
from apps.orders.models import Order
from apps.orders.services import OrderCalculationService

ORDER_TOTAL_FIELD_NAMES = {
    'subtotal',
    'stitching_price',
    'tax_amount',
    'delivery_fee',
    'system_fee',
    'measurement_fee',
    'express_fee',
    'total_amount',
}


class OrderTotalsFieldTests(TestCase):
    def test_calculate_all_totals_taxable_base_is_not_an_order_column(self):
        order_field_names = {f.name for f in Order._meta.get_fields()}
        fabric = MagicMock()
        fabric.is_on_sale = False
        fabric.is_sale_active = False
        fabric.discount_price = None
        fabric.price = Decimal('10.00')
        fabric.stitching_price = Decimal('5.00')
        totals = OrderCalculationService.calculate_all_totals(
            [{'fabric': fabric, 'quantity': 1}],
            order_type='fabric_with_stitching',
            service_mode='walk_in',
        )
        self.assertIn('taxable_base', totals)
        self.assertNotIn('taxable_base', order_field_names)
        extra_keys = set(totals.keys()) - ORDER_TOTAL_FIELD_NAMES - {'taxable_base'}
        self.assertEqual(extra_keys, set())


class WalkInVatCalculationTests(TestCase):
    def _fabric(self, price='100.00', stitching_price='30.00'):
        fabric = MagicMock()
        fabric.is_on_sale = False
        fabric.is_sale_active = False
        fabric.discount_price = None
        fabric.price = Decimal(price)
        fabric.stitching_price = Decimal(stitching_price)
        return fabric

    def test_fabric_with_stitching_walk_in_taxes_both(self):
        fabric = self._fabric('92.00', '21.00')
        items = [{'fabric': fabric, 'quantity': 1}]
        totals = OrderCalculationService.calculate_all_totals(
            items,
            order_type='fabric_with_stitching',
            service_mode='walk_in',
        )
        self.assertEqual(totals['subtotal'], Decimal('92.00'))
        self.assertEqual(totals['stitching_price'], Decimal('21.00'))
        self.assertEqual(totals['taxable_base'], Decimal('113.00'))
        self.assertEqual(totals['tax_amount'], Decimal('16.95'))
        self.assertEqual(totals['total_amount'], Decimal('129.95'))

    def test_stitching_only_walk_in_taxes_stitching(self):
        totals = OrderCalculationService.calculate_all_totals(
            [{'fabric': None, 'quantity': 1}],
            order_type='stitching_only',
            service_mode='walk_in',
            manual_stitching_price=Decimal('150.00'),
        )
        self.assertEqual(totals['stitching_price'], Decimal('150.00'))
        self.assertEqual(totals['taxable_base'], Decimal('150.00'))
        self.assertEqual(totals['tax_amount'], Decimal('22.50'))
        self.assertEqual(totals['total_amount'], Decimal('172.50'))

    def test_home_delivery_fabric_with_stitching_taxes_both(self):
        fabric = self._fabric('100.00', '30.00')
        items = [{'fabric': fabric, 'quantity': 1}]
        totals = OrderCalculationService.calculate_all_totals(
            items,
            order_type='fabric_with_stitching',
            service_mode='home_delivery',
        )
        self.assertEqual(totals['subtotal'], Decimal('100.00'))
        self.assertEqual(totals['stitching_price'], Decimal('30.00'))
        self.assertEqual(totals['taxable_base'], Decimal('130.00'))
        self.assertEqual(totals['tax_amount'], Decimal('19.50'))

    def test_walk_in_fabric_only_taxes_subtotal(self):
        fabric = self._fabric('80.00', '0.00')
        items = [{'fabric': fabric, 'quantity': 1}]
        totals = OrderCalculationService.calculate_all_totals(
            items,
            order_type='fabric_only',
            service_mode='walk_in',
        )
        self.assertEqual(totals['taxable_base'], Decimal('80.00'))
        self.assertEqual(totals['tax_amount'], Decimal('12.00'))

    def test_calculate_order_taxable_base_includes_express(self):
        base = OrderCalculationService.calculate_order_taxable_base(
            Decimal('92.00'),
            Decimal('21.00'),
            'fabric_with_stitching',
            express_fee=Decimal('50.00'),
        )
        self.assertEqual(base, Decimal('163.00'))


class ZatcaLineBuilderTests(TestCase):
    def _order(self, **kwargs):
        defaults = {
            'service_mode': 'walk_in',
            'order_type': 'fabric_with_stitching',
            'subtotal': Decimal('92.00'),
            'stitching_price': Decimal('21.00'),
        }
        defaults.update(kwargs)
        return Order(**defaults)

    def test_fabric_with_stitching_lines(self):
        lines = build_zatca_lines_for_order(self._order())
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0]['name'], 'Fabric')
        self.assertEqual(lines[1]['name'], 'Stitching')

    def test_stitching_only_single_line(self):
        order = self._order(
            order_type='stitching_only',
            subtotal=Decimal('0.00'),
            stitching_price=Decimal('150.00'),
        )
        lines = build_zatca_lines_for_order(order)
        self.assertEqual(len(lines), 1)
        self.assertIn('customer-supplied', lines[0]['description'])


@override_settings(ZATCA_INVOICING_ENABLED=True, ZATCA_TOOLS_API_KEY='ztk_test_key')
class WalkInInvoiceServiceTests(TestCase):
    @patch('apps.invoicing.services.walk_in_invoice.ZatcaToolsClient')
    def test_issue_persists_accepted_invoice(self, client_cls):
        client = client_cls.return_value
        client.configured = True
        client.create_simplified_invoice.return_value = {
            'number': 'TRY-INV-2026-00099',
            'uuid': '80004936-4b5f-42a9-b086-68b555774cef',
            'status': 'accepted',
            'totals': {'taxable': '113.00', 'vat': '16.95', 'grand': '129.95'},
            'zatca': {'channel': 'reporting', 'icv': 3},
            'links': {'view': 'https://zatcatools.com/invoice/x', 'pdf': None, 'xml': None},
        }

        from apps.accounts.models import CustomUser

        customer = CustomUser.objects.create_user(username='cust1', password='x', phone='0500000001')
        tailor = CustomUser.objects.create_user(username='tail1', password='x', phone='0500000002', role='TAILOR')
        order = Order.objects.create(
            customer=customer,
            tailor=tailor,
            order_type='fabric_with_stitching',
            service_mode='walk_in',
            payment_status='paid',
            subtotal=Decimal('92.00'),
            stitching_price=Decimal('21.00'),
            tax_amount=Decimal('16.95'),
            total_amount=Decimal('129.95'),
        )

        result = issue_walk_in_tax_invoice(order.id)
        self.assertIsNotNone(result)
        self.assertEqual(result.status, 'accepted')
        self.assertEqual(result.provider_number, 'TRY-INV-2026-00099')
        client.create_simplified_invoice.assert_called_once()

    @override_settings(ZATCA_INVOICING_ENABLED=True, ZATCA_TOOLS_API_KEY='')
    def test_issue_without_api_key_creates_failed_row_not_silent_skip(self):
        from apps.accounts.models import CustomUser

        customer = CustomUser.objects.create_user(username='cust2', password='x', phone='0500000011')
        tailor = CustomUser.objects.create_user(username='tail2', password='x', phone='0500000012', role='TAILOR')
        order = Order.objects.create(
            customer=customer,
            tailor=tailor,
            order_type='fabric_with_stitching',
            service_mode='walk_in',
            payment_status='paid',
            subtotal=Decimal('92.00'),
            stitching_price=Decimal('21.00'),
            tax_amount=Decimal('16.95'),
            total_amount=Decimal('129.95'),
        )
        result = issue_walk_in_tax_invoice(order.id)
        self.assertIsNotNone(result)
        self.assertEqual(result.status, 'failed')
        self.assertEqual(result.error_code, 'not_configured')
