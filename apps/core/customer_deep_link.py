"""Customer app order deep link helpers (WhatsApp / Universal Links)."""

from __future__ import annotations

import copy
import json
import logging
import re
from pathlib import Path
from typing import Any, Optional

from django.conf import settings

logger = logging.getLogger(__name__)

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


def customer_app_custom_scheme() -> str:
    return (getattr(settings, 'CUSTOMER_APP_CUSTOM_SCHEME', 'mgask') or 'mgask').strip().rstrip(':')


def custom_scheme_order_url(order_id: int) -> str:
    return f'{customer_app_custom_scheme()}://order/{int(order_id)}'


def _deeplink_ops_dir() -> Path:
    configured = getattr(settings, 'CUSTOMER_APP_DEEPLINK_OPS_DIR', None)
    if configured:
        return Path(configured)
    return Path(settings.BASE_DIR) / 'ops' / 'deeplink'


def _read_ops_json(filename: str) -> Any | None:
    path = _deeplink_ops_dir() / filename
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning('Failed to read deep link ops file %s: %s', path, exc)
        return None


def build_android_assetlinks_payload() -> list[dict[str, Any]]:
    """Merge ops/deeplink/assetlinks.json with env overrides."""
    data = _read_ops_json('assetlinks.json')
    if not isinstance(data, list) or not data:
        package = customer_app_android_package()
        data = [
            {
                'relation': ['delegate_permission/common.handle_all_urls'],
                'target': {
                    'namespace': 'android_app',
                    'package_name': package,
                    'sha256_cert_fingerprints': [],
                },
            }
        ]
    else:
        data = copy.deepcopy(data)

    env_fps = customer_app_android_sha256_list()
    package = customer_app_android_package()
    for entry in data:
        target = entry.get('target')
        if not isinstance(target, dict):
            continue
        if package:
            target['package_name'] = package
        if env_fps:
            target['sha256_cert_fingerprints'] = env_fps
            continue
        fingerprints = target.get('sha256_cert_fingerprints')
        if not isinstance(fingerprints, list):
            fingerprints = []
        normalized: list[str] = []
        for fp in fingerprints:
            text = str(fp).strip()
            if not text or 'PASTE' in text.upper() or 'REPLACE' in text.upper():
                continue
            parsed = _normalize_sha256_fingerprint(text)
            if parsed:
                normalized.append(parsed)
        target['sha256_cert_fingerprints'] = normalized

    fps = data[0].get('target', {}).get('sha256_cert_fingerprints', [])
    if not fps:
        return []

    return data


def _normalize_sha256_fingerprint(raw: str) -> str | None:
    fp = raw.strip().upper().replace(':', '').replace(' ', '')
    if len(fp) != 64 or not all(c in '0123456789ABCDEF' for c in fp):
        return None
    return ':'.join(fp[i : i + 2] for i in range(0, 64, 2))


def build_apple_app_site_association_payload() -> dict[str, Any]:
    """Merge ops/deeplink/apple-app-site-association.json with env overrides."""
    data = _read_ops_json('apple-app-site-association.json')
    if not isinstance(data, dict):
        data = {'applinks': {'apps': [], 'details': []}}
    else:
        data = copy.deepcopy(data)

    app_id = customer_app_apple_app_id()
    paths = customer_order_link_paths()
    applinks = data.setdefault('applinks', {})
    details = applinks.setdefault('details', [])
    if not details or not isinstance(details[0], dict):
        if app_id:
            applinks['details'] = [{'appID': app_id, 'paths': paths}]
        else:
            return {'applinks': {'apps': [], 'details': []}}
    else:
        if app_id:
            details[0]['appID'] = app_id
        details[0]['paths'] = paths

    if not applinks.get('details'):
        return {'applinks': {'apps': [], 'details': []}}

    return data
