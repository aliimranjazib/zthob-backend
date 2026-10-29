from decimal import Decimal

from django.core.exceptions import ValidationError

from apps.orders.services import OrderCalculationService


def _money(value) -> Decimal:
    return Decimal(str(value or '0')).quantize(Decimal('0.01'))


def _append_express_line(lines: list[dict], express_fee: Decimal) -> None:
    if express_fee <= Decimal('0.00'):
        return
    lines.append(
        {
            'name': 'Express service',
            'description': 'Express stitching service',
            'quantity': 1,
            'unit_price': float(express_fee),
            'tax_category': 'S',
        }
    )


def build_zatca_lines_for_order(order) -> list[dict]:
    """
    Build ZATCA Tools line payloads (ex-VAT unit prices) for walk-in orders.
    """
    if order.service_mode != 'walk_in':
        raise ValidationError('Tax invoices are supported for walk-in orders only.')

    order_type = order.order_type
    subtotal = _money(order.subtotal)
    stitching = _money(order.stitching_price)
    express_fee = _money(order.express_fee)

    if order_type == 'fabric_with_stitching':
        if subtotal <= Decimal('0.00'):
            raise ValidationError('Fabric subtotal is required for fabric + stitching orders.')
        if stitching <= Decimal('0.00'):
            raise ValidationError('Stitching price is required for fabric + stitching orders.')
        lines = [
            {
                'name': 'Fabric',
                'description': 'Fabric supplied by shop',
                'quantity': 1,
                'unit_price': float(subtotal),
                'tax_category': 'S',
            },
            {
                'name': 'Stitching',
                'description': 'Tailoring / stitching service',
                'quantity': 1,
                'unit_price': float(stitching),
                'tax_category': 'S',
            },
        ]
        _append_express_line(lines, express_fee)
        return lines

    if order_type == 'stitching_only':
        if stitching <= Decimal('0.00'):
            raise ValidationError('Stitching price is required for stitching-only orders.')
        lines = [
            {
                'name': 'Stitching',
                'description': 'Stitching service — customer-supplied fabric',
                'quantity': 1,
                'unit_price': float(stitching),
                'tax_category': 'S',
            },
        ]
        _append_express_line(lines, express_fee)
        return lines

    if order_type == 'fabric_only':
        if subtotal <= Decimal('0.00'):
            raise ValidationError('Fabric subtotal is required for fabric-only orders.')
        lines = [
            {
                'name': 'Fabric',
                'description': 'Fabric supplied by shop',
                'quantity': 1,
                'unit_price': float(subtotal),
                'tax_category': 'S',
            },
        ]
        _append_express_line(lines, express_fee)
        return lines

    raise ValidationError(f'Order type {order_type} is not supported for walk-in tax invoicing.')


def expected_zatca_taxable_amount(order) -> Decimal:
    """Match order VAT base used in OrderCalculationService."""
    return OrderCalculationService.calculate_order_taxable_base(
        order.subtotal,
        order.stitching_price,
        order.order_type,
        express_fee=order.express_fee,
    )
