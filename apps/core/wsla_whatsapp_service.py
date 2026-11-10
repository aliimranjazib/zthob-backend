"""WSLA Official WhatsApp Meta API client."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any

from django.conf import settings

from apps.core.phone_format import format_phone_e164

logger = logging.getLogger(__name__)


class WslaWhatsAppService:
    @staticmethod
    def _is_configured() -> tuple[bool, str]:
        if not getattr(settings, 'WSLA_WHATSAPP_ENABLED', False):
            return False, 'WSLA WhatsApp is disabled (WSLA_WHATSAPP_ENABLED)'
        token = (getattr(settings, 'WSLA_WHATSAPP_TOKEN', None) or '').strip()
        if not token:
            return False, 'WSLA not configured. Missing WSLA_WHATSAPP_TOKEN'
        return True, ''

    @staticmethod
    def format_number_for_wsla(phone_number: str) -> str:
        """WSLA expects digits only, e.g. 966501234567."""
        return format_phone_e164(phone_number).lstrip('+')

    @staticmethod
    def send_template(
        *,
        phone_number: str,
        template_name: str,
        language: str,
        body_parameters: list[str],
        url_button_suffix: str | None = None,
        url_button_index: str | None = None,
    ) -> tuple[bool, str, str | None]:
        """
        Send an approved WhatsApp template.

        Returns (success, detail_message, provider_message_id).
        """
        configured, error = WslaWhatsAppService._is_configured()
        if not configured:
            return False, error, None

        template_name = (template_name or '').strip()
        if not template_name:
            return False, 'Template name is required', None

        number = WslaWhatsAppService.format_number_for_wsla(phone_number)
        if not number:
            return False, 'Recipient phone number is required', None

        parameters = [
            {'type': 'text', 'text': str(value if value is not None else '-').strip() or '-'}
            for value in body_parameters
        ]

        components: list[dict[str, Any]] = [
            {
                'type': 'body',
                'parameters': parameters,
            }
        ]

        suffix = (url_button_suffix or '').strip()
        if suffix:
            button_index = (url_button_index or getattr(settings, 'WSLA_URL_BUTTON_INDEX', '0') or '0').strip()
            components.append(
                {
                    'type': 'button',
                    'sub_type': 'url',
                    'index': button_index,
                    'parameters': [
                        {
                            'type': 'text',
                            'text': suffix[:2000],
                        }
                    ],
                }
            )

        payload: dict[str, Any] = {
            'number': number,
            'templateName': template_name,
            'language': language or getattr(settings, 'WSLA_TEMPLATE_LANG', 'ar'),
            'components': components,
        }

        base_url = (getattr(settings, 'WSLA_BASE_URL', 'https://api.wsla.io') or '').rstrip('/')
        url = f'{base_url}/api/oficial/send/template'
        body = json.dumps(payload).encode('utf-8')
        timeout = int(getattr(settings, 'WSLA_TIMEOUT_SECONDS', 30))

        request = urllib.request.Request(
            url,
            data=body,
            method='POST',
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {settings.WSLA_WHATSAPP_TOKEN}',
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read().decode('utf-8')
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode('utf-8') if exc.fp else str(exc)
            logger.error('WSLA WhatsApp HTTP error: %s - %s', exc.code, raw)
            return False, f'Failed to send WhatsApp: HTTP {exc.code}', None
        except urllib.error.URLError as exc:
            logger.error('WSLA WhatsApp connection error: %s', exc)
            return False, 'Failed to contact WSLA WhatsApp API', None

        try:
            parsed = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            logger.error('WSLA WhatsApp invalid JSON: %s', raw)
            return False, 'Invalid response from WSLA WhatsApp API', None

        if isinstance(parsed, dict):
            status = (parsed.get('status') or '').upper()
            if status and status not in ('SUCCESS', 'OK', 'ACCEPTED'):
                detail = parsed.get('message') or parsed.get('error') or raw
                return False, f'WSLA WhatsApp rejected send: {detail}', None

            message_id = parsed.get('messageId') or parsed.get('message_id')
            data = parsed.get('data')
            if message_id is None and isinstance(data, dict):
                message_id = data.get('messageId') or data.get('id')
            message_id = str(message_id) if message_id else None
            logger.info(
                'WSLA WhatsApp template sent. template=%s number=%s*** messageId=%s',
                template_name,
                number[:6],
                message_id,
            )
            return True, 'WhatsApp template sent', message_id

        return True, 'WhatsApp template sent', None
