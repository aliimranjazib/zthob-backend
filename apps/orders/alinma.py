import base64
import hashlib
import json
import logging
from dataclasses import dataclass
from typing import Any

import requests
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from django.conf import settings


logger = logging.getLogger(__name__)


class AlinmaConfigurationError(Exception):
    """Raised when required Alinma settings are missing."""


class AlinmaGatewayError(Exception):
    """Raised when Alinma returns an invalid or failed response."""


@dataclass(frozen=True)
class AlinmaConfig:
    terminal_id: str
    terminal_password: str
    merchant_key: str
    currency: str
    request_url: str
    receipt_base_url: str
    request_timeout: int


def get_alinma_config() -> AlinmaConfig:
    terminal_id = getattr(settings, 'ALINMAPAY_TERMINAL_ID', '')
    terminal_password = getattr(settings, 'ALINMAPAY_TERMINAL_PASSWORD', '')
    merchant_key = getattr(settings, 'ALINMAPAY_MERCHANT_KEY', '')
    request_url = getattr(settings, 'ALINMAPAY_REQUEST_URL', '')
    currency = getattr(settings, 'ALINMAPAY_CURRENCY', 'SAR')
    receipt_base_url = getattr(settings, 'ALINMAPAY_RECEIPT_BASE_URL', '')
    request_timeout = int(getattr(settings, 'ALINMAPAY_TIMEOUT_SECONDS', 30))

    if not terminal_id or not terminal_password or not merchant_key or not request_url:
        raise AlinmaConfigurationError(
            'Alinma Pay is not fully configured. '
            'Set ALINMAPAY_TERMINAL_ID, ALINMAPAY_TERMINAL_PASSWORD, '
            'ALINMAPAY_MERCHANT_KEY, and ALINMAPAY_REQUEST_URL.'
        )

    return AlinmaConfig(
        terminal_id=terminal_id,
        terminal_password=terminal_password,
        merchant_key=merchant_key,
        currency=currency,
        request_url=request_url,
        receipt_base_url=receipt_base_url,
        request_timeout=request_timeout,
    )


def build_request_signature(track_id: str, amount: str, currency: str, config: AlinmaConfig) -> str:
    raw = (
        f'{track_id}|{config.terminal_id}|{config.terminal_password}|'
        f'{config.merchant_key}|{amount}|{currency}'
    )
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def build_response_signature(payment_id: str, response_code: str, amount: str, config: AlinmaConfig) -> str:
    raw = f'{payment_id}|{config.merchant_key}|{response_code}|{amount}'
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def initiate_hosted_payment(
    *,
    track_id: str,
    amount: str,
    order_id: str,
    description: str,
    receipt_url: str,
    customer: dict[str, Any] | None = None,
    user_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = get_alinma_config()
    signature = build_request_signature(
        track_id=track_id,
        amount=amount,
        currency=config.currency,
        config=config,
    )
    payload: dict[str, Any] = {
        'trackId': track_id,
        'terminalId': config.terminal_id,
        'password': config.terminal_password,
        'signature': signature,
        'paymentType': '1',
        'amount': amount,
        'currency': config.currency,
        'order': {
            'orderId': order_id,
            'description': description,
        },
        'additionalDetails': {
            'userData': json.dumps({
                **(user_data or {}),
                'receiptUrl': receipt_url,
            }),
        },
    }
    if customer:
        payload['customer'] = customer

    logger.info(
        'Initiating Alinma hosted payment: request_url=%s track_id=%s order_id=%s amount=%s currency=%s receipt_url=%s',
        config.request_url,
        track_id,
        order_id,
        amount,
        config.currency,
        receipt_url,
    )

    try:
        response = requests.post(
            config.request_url,
            json=payload,
            timeout=config.request_timeout,
        )
    except requests.RequestException as exc:
        logger.exception(
            'Failed to connect to Alinma Pay: request_url=%s track_id=%s order_id=%s',
            config.request_url,
            track_id,
            order_id,
        )
        raise AlinmaGatewayError('Could not connect to Alinma Pay.') from exc

    logger.info(
        'Alinma Pay response received: track_id=%s order_id=%s status_code=%s',
        track_id,
        order_id,
        response.status_code,
    )

    try:
        data = response.json()
    except ValueError as exc:
        logger.error(
            'Alinma Pay returned non-JSON response: track_id=%s order_id=%s status_code=%s body=%s',
            track_id,
            order_id,
            response.status_code,
            response.text[:1000],
        )
        raise AlinmaGatewayError('Alinma Pay returned an unreadable response.') from exc

    if response.status_code >= 400:
        logger.error(
            'Alinma Pay rejected payment initiation: track_id=%s order_id=%s status_code=%s response=%s',
            track_id,
            order_id,
            response.status_code,
            json.dumps(data)[:1000],
        )
        raise AlinmaGatewayError(
            data.get('responseDescription')
            or data.get('message')
            or 'Alinma Pay rejected the payment initiation request.'
        )

    logger.info(
        'Alinma Pay initiation succeeded: track_id=%s order_id=%s transaction_id=%s response_code=%s',
        track_id,
        order_id,
        data.get('transactionId'),
        data.get('responseCode'),
    )

    return data


def decrypt_callback_payload(encrypted_data: str, merchant_key: str) -> str:
    key = bytes.fromhex(merchant_key)
    decoded = base64.b64decode(encrypted_data)
    cipher = Cipher(algorithms.AES(key), modes.ECB(), backend=default_backend())
    decryptor = cipher.decryptor()
    decrypted = decryptor.update(decoded) + decryptor.finalize()
    unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
    unpadded = unpadder.update(decrypted) + unpadder.finalize()
    return unpadded.decode('utf-8')


def parse_callback_payload(encrypted_data: str) -> dict[str, Any]:
    config = get_alinma_config()
    raw = decrypt_callback_payload(encrypted_data, config.merchant_key)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error('Failed to decode decrypted Alinma callback payload: %s', raw)
        raise AlinmaGatewayError('Alinma Pay callback payload could not be parsed.') from exc


def response_amount(payload: dict[str, Any]) -> str:
    amount_details = payload.get('amountDetails') or {}
    return str(amount_details.get('amount') or payload.get('amount') or '0.00')


def verify_callback_signature(payload: dict[str, Any]) -> bool:
    signature = payload.get('signature')
    transaction_id = str(payload.get('transactionId') or '')
    response_code = str(payload.get('responseCode') or '')
    amount = response_amount(payload)

    if not signature or not transaction_id or not response_code:
        return False

    expected = build_response_signature(
        payment_id=transaction_id,
        response_code=response_code,
        amount=amount,
        config=get_alinma_config(),
    )
    return signature.lower() == expected.lower()


def is_successful_callback(payload: dict[str, Any]) -> bool:
    response_code = str(payload.get('responseCode') or '')
    result = str(payload.get('result') or payload.get('status') or '').upper()
    return response_code in {'00', '000', '001'} or result == 'SUCCESS'
