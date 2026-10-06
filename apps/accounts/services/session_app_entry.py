"""Resolve app_entry from HTTP request vs JWT for session-scoped auth."""

from __future__ import annotations

APP_ENTRY_OWNER = 'owner'
_VALID_ENTRIES = frozenset({'owner', 'staff', 'tailor'})


def _normalize_app_entry(value: str) -> str | None:
    normalized = value.strip().lower()
    if normalized not in _VALID_ENTRIES:
        return normalized
    return normalized


def _read_token_claim(request, key: str) -> str | None:
    if request is None:
        return None
    token = getattr(request, 'auth', None)
    if token is None:
        return None
    if not hasattr(token, 'get'):
        return None
    value = token.get(key)
    if value in (None, ''):
        return None
    return str(value).strip().lower()


def get_token_app_entry(request) -> str | None:
    """JWT ``app_entry`` claim from the access token (authoritative for owner APIs)."""
    raw = _read_token_claim(request, 'app_entry')
    if raw is None:
        return None
    return _normalize_app_entry(raw)


def get_request_app_entry(request) -> str | None:
    """Explicit app_entry from query or header (response shaping on /v2/me, profile)."""
    if request is None:
        return None
    query = getattr(request, 'query_params', None)
    if query is not None:
        q = query.get('app_entry')
        if q not in (None, ''):
            return _normalize_app_entry(str(q).strip())
    headers = getattr(request, 'headers', None)
    header = None
    if headers is not None:
        header = headers.get('X-App-Entry')
    if not header:
        meta = getattr(request, 'META', {}) or {}
        header = meta.get('HTTP_X_APP_ENTRY')
    if header not in (None, ''):
        return _normalize_app_entry(str(header).strip())
    return None


def has_owner_platform_jwt(request) -> bool:
    return get_token_app_entry(request) == APP_ENTRY_OWNER
