import logging
from decimal import Decimal

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from apps.core.phone_utils import display_user_label
from apps.invoicing.line_builder import build_zatca_lines_for_order, expected_zatca_taxable_amount
from apps.invoicing.models import TaxInvoice
from apps.invoicing.providers.zatca_tools import ZatcaToolsClient, ZatcaToolsError
from django.core.exceptions import ValidationError

from apps.orders.models import Order

logger = logging.getLogger(__name__)

WALK_IN_INVOICE_ORDER_TYPES = frozenset(
    {'fabric_with_stitching', 'stitching_only', 'fabric_only'}
)


def walk_in_invoicing_enabled() -> bool:
    return bool(getattr(settings, 'ZATCA_INVOICING_ENABLED', False))


def should_issue_walk_in_tax_invoice(order: Order) -> bool:
    if not walk_in_invoicing_enabled():
        return False
    if order.service_mode != 'walk_in' or order.payment_status != 'paid':
        return False
    if order.order_type not in WALK_IN_INVOICE_ORDER_TYPES:
        return False
    return True


def _customer_payload(order: Order) -> dict:
    customer = order.customer
    name = display_user_label(customer) if customer else 'Customer'
    payload = {'name': name}
    if customer and customer.phone:
        payload['phone'] = customer.phone
    shop_name = ''
    if order.shop and order.shop.shop_name:
        shop_name = order.shop.shop_name
    payload['printed_details'] = f'Mgask {order.order_number} · {shop_name}'.strip(' ·')
    return payload


def _map_api_status(api_status: str) -> str:
    normalized = (api_status or '').lower()
    if normalized == 'accepted':
        return TaxInvoice.STATUS_ACCEPTED
    if normalized == 'warnings':
        return TaxInvoice.STATUS_WARNINGS
    if normalized == 'rejected':
        return TaxInvoice.STATUS_REJECTED
    return TaxInvoice.STATUS_FAILED


def _parse_totals(data: dict) -> tuple[Decimal, Decimal, Decimal]:
    totals = data.get('totals') or {}
    return (
        Decimal(str(totals.get('taxable', '0') or '0')),
        Decimal(str(totals.get('vat', '0') or '0')),
        Decimal(str(totals.get('grand', '0') or '0')),
    )


def issue_walk_in_tax_invoice(order_id: int) -> TaxInvoice | None:
    if not walk_in_invoicing_enabled():
        return None

    with transaction.atomic():
        order = (
            Order.objects.select_related('customer', 'shop')
            .select_for_update(of=('self',))
            .filter(pk=order_id)
            .first()
        )
        if not order:
            logger.warning('issue_walk_in_tax_invoice: order %s not found', order_id)
            return None

        if not should_issue_walk_in_tax_invoice(order):
            return None

        existing = TaxInvoice.objects.filter(order=order).first()
        if existing and existing.is_success:
            return existing

        external_id = order.order_number
        tax_invoice = existing or TaxInvoice(
            order=order,
            shop=order.shop,
            external_id=external_id,
        )
        tax_invoice.status = TaxInvoice.STATUS_SUBMITTING
        tax_invoice.error_code = ''
        tax_invoice.error_message = ''
        tax_invoice.save()

    client = ZatcaToolsClient()
    if not client.configured:
        tax_invoice.status = TaxInvoice.STATUS_FAILED
        tax_invoice.error_code = 'not_configured'
        tax_invoice.error_message = 'ZATCA_TOOLS_API_KEY is not configured.'
        tax_invoice.save(update_fields=['status', 'error_code', 'error_message', 'updated_at'])
        return tax_invoice

    try:
        lines = build_zatca_lines_for_order(order)
        line_net = sum(Decimal(str(line['unit_price'])) * Decimal(str(line['quantity'])) for line in lines)
        expected_net = expected_zatca_taxable_amount(order)
        if abs(line_net - expected_net) > Decimal('0.02'):
            raise ValidationError(
                f'Invoice line total {line_net} does not match order taxable base {expected_net}.'
            )
    except Exception as exc:
        tax_invoice.status = TaxInvoice.STATUS_FAILED
        tax_invoice.error_code = 'invalid_order'
        tax_invoice.error_message = str(exc)
        tax_invoice.save(update_fields=['status', 'error_code', 'error_message', 'updated_at'])
        return tax_invoice

    payload = {
        'external_id': external_id,
        'prices_include_vat': False,
        'customer': _customer_payload(order),
        'notes': getattr(settings, 'MGASK_INVOICE_BRAND_NAME', 'Mgask for Tailors'),
        'lines': lines,
    }
    branch_id = getattr(settings, 'ZATCA_TOOLS_BRANCH_ID', None)
    device_id = getattr(settings, 'ZATCA_TOOLS_DEVICE_ID', None)
    if branch_id and device_id:
        payload['branch_id'] = int(branch_id)
        payload['device_id'] = int(device_id)

    try:
        data = client.create_simplified_invoice(payload, idempotency_key=external_id)
    except ZatcaToolsError as exc:
        tax_invoice.status = TaxInvoice.STATUS_FAILED
        tax_invoice.error_code = exc.code
        tax_invoice.error_message = exc.message
        tax_invoice.save(update_fields=['status', 'error_code', 'error_message', 'updated_at'])
        return tax_invoice
    except Exception as exc:
        logger.exception('ZATCA invoice failed for order %s', order_id)
        tax_invoice.status = TaxInvoice.STATUS_FAILED
        tax_invoice.error_code = 'network_error'
        tax_invoice.error_message = str(exc)
        tax_invoice.save(update_fields=['status', 'error_code', 'error_message', 'updated_at'])
        return tax_invoice

    taxable, vat, grand = _parse_totals(data)
    zatca = data.get('zatca') or {}
    links = data.get('links') or {}
    tax_invoice.provider_number = data.get('number') or ''
    tax_invoice.uuid = data.get('uuid') or None
    tax_invoice.status = _map_api_status(data.get('status'))
    tax_invoice.zatca_channel = zatca.get('channel') or ''
    tax_invoice.zatca_icv = zatca.get('icv')
    tax_invoice.taxable_amount = taxable
    tax_invoice.vat_amount = vat
    tax_invoice.grand_total = grand
    tax_invoice.view_url = links.get('view') or ''
    tax_invoice.raw_response = data
    tax_invoice.issued_at = timezone.now()
    tax_invoice.error_code = ''
    tax_invoice.error_message = ''

    if tax_invoice.status == TaxInvoice.STATUS_REJECTED:
        rejection = zatca.get('rejection') or data.get('rejection') or 'Rejected by ZATCA'
        tax_invoice.error_message = str(rejection)

    pdf_url = links.get('pdf')
    xml_url = links.get('xml')
    if pdf_url and tax_invoice.status in (TaxInvoice.STATUS_ACCEPTED, TaxInvoice.STATUS_WARNINGS):
        try:
            pdf_bytes = client.download_binary(pdf_url)
            filename = f'{external_id}.pdf'
            tax_invoice.pdf_file.save(filename, ContentFile(pdf_bytes), save=False)
        except Exception:
            logger.exception('Failed to download tax invoice PDF for %s', external_id)
    if xml_url and tax_invoice.status in (TaxInvoice.STATUS_ACCEPTED, TaxInvoice.STATUS_WARNINGS):
        try:
            xml_bytes = client.download_binary(xml_url)
            filename = f'{external_id}.xml'
            tax_invoice.xml_file.save(filename, ContentFile(xml_bytes), save=False)
        except Exception:
            logger.exception('Failed to download tax invoice XML for %s', external_id)

    tax_invoice.save()
    return tax_invoice


def schedule_walk_in_tax_invoice(order_id: int) -> None:
    if not walk_in_invoicing_enabled():
        logger.info(
            'Skipping walk-in tax invoice for order %s (ZATCA_INVOICING_ENABLED is false)',
            order_id,
        )
        return

    def _dispatch():
        from apps.invoicing.tasks import issue_walk_in_tax_invoice_task

        if getattr(settings, 'ZATCA_INVOICE_ISSUE_SYNC', False):
            issue_walk_in_tax_invoice(order_id)
            return
        try:
            issue_walk_in_tax_invoice_task.delay(order_id)
        except Exception:
            logger.exception(
                'Celery unavailable; issuing walk-in tax invoice synchronously for order %s',
                order_id,
            )
            issue_walk_in_tax_invoice(order_id)

    transaction.on_commit(_dispatch)
