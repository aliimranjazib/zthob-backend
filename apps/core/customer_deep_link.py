"""Customer app order deep link helpers (WhatsApp / Universal Links)."""

from __future__ import annotations

import re
from typing import Optional

from django.conf import settings

_ORDER_ID_RE = re.compile(r'^[1-9]\d{0,18}$')


def parse_order_id_from_path(value: str | None) -> Optional[int]:
    """Return positive integer order id or None for invalid input."""
    if value is None:
        return None
    raw = str(value).strip().strip('/')
    if not raw or not _ORDER_ID_RE.fullmatch(raw):
        return None
    try:
        order_id = int(raw)
    except (TypeError, ValueError):
        return None
    if order_id < 1:
        return None
    return order_id


def walk_in_whatsapp_url_button_suffix(order_id: int) -> str:
    """Dynamic URL suffix for Meta template button (base is static in Meta)."""
    return str(int(order_id))


def customer_app_android_package() -> str:
    return (getattr(settings, 'CUSTOMER_APP_ANDROID_PACKAGE', 'com.mgask.customerapp') or '').strip()


def customer_app_ios_bundle_id() -> str:
    return (getattr(settings, 'CUSTOMER_APP_IOS_BUNDLE_ID', 'com.mgask.customerapp') or '').strip()


def customer_app_android_sha256_list() -> list[str]:
    raw = getattr(settings, 'CUSTOMER_APP_ANDROID_SHA256_FINGERPRINTS', '') or ''
    items = []
    for part in str(raw).replace(';', ',').split(','):
        fp = part.strip().upper().replace(':', '')
        if len(fp) == 64 and all(c in '0123456789ABCDEF' for c in fp):
            # assetlinks.json uses colon-separated pairs
            formatted = ':'.join(fp[i : i + 2] for i in range(0, 64, 2))
            items.append(formatted)
    return items


def customer_app_apple_app_id() -> str | None:
    team = (getattr(settings, 'CUSTOMER_APP_APPLE_TEAM_ID', '') or '').strip()
    bundle = customer_app_ios_bundle_id()
    if not team or not bundle:
        return None
    return f'{team}.{bundle}'


def customer_order_link_paths() -> list[str]:
    pattern = (getattr(settings, 'CUSTOMER_ORDER_DEEP_LINK_PATH_PATTERN', '/order/*') or '/order/*').strip()
    return [pattern or '/order/*']
