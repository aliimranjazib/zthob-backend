import base64
import hashlib
import hmac
import logging
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse

import requests
from django.conf import settings


logger = logging.getLogger(__name__)


ALLOWED_API_HOSTS = {
    'api-sa.myfatoorah.com',
    'apitest.myfatoorah.com',
}

CURRENCY_ALIASES = {
    'KD': 'KWD',
}

# MyFatoorah's test gateway occasionally returns the misspelled status "Succss".
SUCCESSFUL_TRANSACTION_STATUSES = {'SUCCESS', 'SUCCSS'}


class MyFatoorahConfigurationError(Exception):
    pass


class MyFatoorahGatewayError(Exception):
    pass


@dataclass(frozen=True)
class MyFatoorahConfig:
    api_key: str
    api_base_url: str
    webhook_secret: str
    timeout_seconds: int
    currency: str = 'SAR'
    country: str = 'SAU'


@dataclass(frozen=True)
class PaymentDetails:
    invoice_id: str
    invoice_status: str
    invoice_value: Decimal
    currency: str
    customer_reference: str
    user_defined_field: str
    transaction_status: str
    payment_id: str
    payment_method: str
    gateway_reference: str

    @property
    def is_paid(self):
        return (
            self.invoice_status == 'PAID'
            and self.transaction_status in SUCCESSFUL_TRANSACTION_STATUSES
        )


def get_myfatoorah_config(*, require_webhook_secret=False):
    api_key = getattr(settings, 'MYFATOORAH_API_KEY', '').strip()
    api_base_url = getattr(settings, 'MYFATOORAH_API_BASE_URL', '').strip().rstrip('/')
    webhook_secret = getattr(settings, 'MYFATOORAH_WEBHOOK_SECRET', '').strip()
    timeout_seconds = int(getattr(settings, 'MYFATOORAH_TIMEOUT_SECONDS', 30))

    if not api_key:
        raise MyFatoorahConfigurationError('MyFatoorah API key is not configured.')
    if require_webhook_secret and not webhook_secret:
        raise MyFatoorahConfigurationError('MyFatoorah webhook secret is not configured.')

    parsed = urlparse(api_base_url)
    if parsed.scheme != 'https' or parsed.hostname not in ALLOWED_API_HOSTS:
        raise MyFatoorahConfigurationError(
            'MyFatoorah API URL must use the Saudi production or official test host.'
        )

    return MyFatoorahConfig(
        api_key=api_key,
        api_base_url=api_base_url,
        webhook_secret=webhook_secret,
        timeout_seconds=timeout_seconds,
        currency=getattr(settings, 'MYFATOORAH_CURRENCY', 'SAR').upper(),
        country=getattr(settings, 'MYFATOORAH_COUNTRY', 'SAU').upper(),
    )


def _normalize_currency(value):
    currency = str(value or '').upper().strip()
    return CURRENCY_ALIASES.get(currency, currency)


def _decimal(value, field_name):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise MyFatoorahGatewayError(f'MyFatoorah returned an invalid {field_name}.') from exc


def _normalize_transaction_status(value):
    status = str(value or '').upper().strip()
    if status == 'SUCCSS':
        return 'SUCCESS'
    return status


def _successful_transaction(transactions):
    for item in transactions:
        raw_status = str(item.get('TransactionStatus') or '').upper()
        if raw_status in SUCCESSFUL_TRANSACTION_STATUSES:
            return item
    return transactions[-1] if transactions else {}


def normalize_payment_details(payload):
    if not payload.get('IsSuccess') or not isinstance(payload.get('Data'), dict):
        message = payload.get('Message') or 'MyFatoorah payment inquiry failed.'
        raise MyFatoorahGatewayError(str(message))

    data = payload['Data']
    transactions = data.get('InvoiceTransactions') or []
    transaction = _successful_transaction(transactions)
    invoice_id = str(data.get('InvoiceId') or '').strip()
    if not invoice_id:
        raise MyFatoorahGatewayError('MyFatoorah response is missing the invoice ID.')

    return PaymentDetails(
        invoice_id=invoice_id,
        invoice_status=str(data.get('InvoiceStatus') or '').upper(),
        invoice_value=_decimal(data.get('InvoiceValue'), 'invoice amount'),
        currency=_normalize_currency(
            transaction.get('PaidCurrency')
            or transaction.get('Currency')
            or data.get('InvoiceDisplayValue', '').split(' ')[-1]
            or ''
        ),
        customer_reference=str(data.get('CustomerReference') or '').strip(),
        user_defined_field=str(data.get('UserDefinedField') or '').strip(),
        transaction_status=_normalize_transaction_status(
            transaction.get('TransactionStatus'),
        ),
        payment_id=str(transaction.get('PaymentId') or '').strip(),
        payment_method=str(transaction.get('PaymentGateway') or '').strip(),
        gateway_reference=str(
            transaction.get('ReferenceId')
            or transaction.get('TransactionId')
            or ''
        ).strip(),
    )


def get_payment_status(invoice_id):
    config = get_myfatoorah_config()
    try:
        response = requests.post(
            f'{config.api_base_url}/v2/GetPaymentStatus',
            headers={
                'Authorization': f'Bearer {config.api_key}',
                'Accept': 'application/json',
                'Content-Type': 'application/json',
            },
            json={'Key': str(invoice_id), 'KeyType': 'InvoiceId'},
            timeout=config.timeout_seconds,
        )
        response.raise_for_status()
    except requests.Timeout as exc:
        raise MyFatoorahGatewayError('MyFatoorah payment verification timed out.') from exc
    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else 'unknown'
        logger.warning(
            'MyFatoorah GetPaymentStatus failed for invoice %s with HTTP %s',
            invoice_id,
            status_code,
        )
        raise MyFatoorahGatewayError(
            f'Could not verify payment with MyFatoorah (HTTP {status_code}).'
        ) from exc
    except requests.RequestException as exc:
        logger.warning(
            'MyFatoorah GetPaymentStatus request failed for invoice %s: %s',
            invoice_id,
            exc,
        )
        raise MyFatoorahGatewayError('Could not verify payment with MyFatoorah.') from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise MyFatoorahGatewayError('MyFatoorah returned an unreadable response.') from exc
    return normalize_payment_details(payload)


def verify_webhook_signature(payload, signature):
    config = get_myfatoorah_config(require_webhook_secret=True)
    invoice = (payload.get('Data') or {}).get('Invoice') or {}
    transaction = (payload.get('Data') or {}).get('Transaction') or {}
    canonical = ','.join([
        f"Invoice.Id={invoice.get('Id') or ''}",
        f"Invoice.Status={invoice.get('Status') or ''}",
        f"Transaction.Status={transaction.get('Status') or ''}",
        f"Transaction.PaymentId={transaction.get('PaymentId') or ''}",
        f"Invoice.ExternalIdentifier={invoice.get('ExternalIdentifier') or ''}",
    ])
    digest = hmac.new(
        config.webhook_secret.encode('utf-8'),
        canonical.encode('utf-8'),
        hashlib.sha256,
    ).digest()
    expected = base64.b64encode(digest).decode('ascii')
    return hmac.compare_digest(expected, str(signature or '').strip())


def payment_metadata(details):
    return {
        'gateway': 'myfatoorah',
        'invoice_id': details.invoice_id,
        'payment_id': details.payment_id,
        'gateway_reference': details.gateway_reference,
        'payment_method': details.payment_method,
        'invoice_status': details.invoice_status,
        'transaction_status': details.transaction_status,
        'currency': details.currency,
    }
