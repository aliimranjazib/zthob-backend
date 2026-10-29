import logging
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class ZatcaToolsError(Exception):
    def __init__(self, code: str, message: str, http_status: int | None = None):
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


class ZatcaToolsClient:
    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self.api_key = (api_key or getattr(settings, 'ZATCA_TOOLS_API_KEY', '') or '').strip()
        self.base_url = (
            base_url or getattr(settings, 'ZATCA_TOOLS_BASE_URL', 'https://zatcatools.com/api') or ''
        ).rstrip('/')
        self.timeout = int(getattr(settings, 'ZATCA_TOOLS_TIMEOUT_SECONDS', 30))

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def _headers(self, idempotency_key: str | None = None) -> dict[str, str]:
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        if idempotency_key:
            headers['Idempotency-Key'] = idempotency_key
        return headers

    def _parse_error(self, response: requests.Response) -> ZatcaToolsError:
        try:
            payload = response.json()
            err = payload.get('error') or {}
            code = err.get('code') or 'http_error'
            message = err.get('message') or response.text or 'Request failed'
        except ValueError:
            code = 'http_error'
            message = response.text or f'HTTP {response.status_code}'
        return ZatcaToolsError(code, message, http_status=response.status_code)

    def get_account(self) -> dict[str, Any]:
        response = requests.get(
            f'{self.base_url}/v1/account',
            headers=self._headers(),
            timeout=self.timeout,
        )
        if not response.ok:
            raise self._parse_error(response)
        return response.json()

    def create_simplified_invoice(self, payload: dict[str, Any], *, idempotency_key: str) -> dict[str, Any]:
        body = {'type': 'simplified', **payload}
        response = requests.post(
            f'{self.base_url}/v1/invoices',
            headers=self._headers(idempotency_key=idempotency_key),
            json=body,
            timeout=self.timeout,
        )
        if response.status_code not in (200, 201):
            raise self._parse_error(response)
        return response.json()

    def download_binary(self, url: str) -> bytes:
        response = requests.get(
            url,
            headers=self._headers(),
            timeout=self.timeout,
        )
        if not response.ok:
            raise self._parse_error(response)
        return response.content
