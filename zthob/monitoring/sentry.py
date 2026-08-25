"""
Sentry initialization and helpers for mgask-backend.

Enabled when SENTRY_DSN is set and APP_ENV is staging/production
(or SENTRY_ENABLED=true in development for local testing).
"""
from __future__ import annotations

import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)

_sentry_initialized = False

_SENSITIVE_HEADERS = frozenset({
    'authorization', 'cookie', 'x-csrftoken', 'x-api-key',
})
_SENSITIVE_FIELD_RE = re.compile(
    r'(password|token|otp|secret|api[_-]?key|authorization|jwt|refresh|access)',
    re.IGNORECASE,
)
_IGNORED_EXCEPTIONS = (
    'django.core.exceptions.DisallowedHost',
    'django.http.response.Http404',
)
_IGNORED_URL_SUFFIXES = (
    '/favicon.ico',
    '/robots.txt',
)

# Longest prefix first so specific journeys win over generic ones.
_JOURNEY_PREFIXES: tuple[tuple[str, str], ...] = (
    ('/api/orders/checkout/myfatoorah', 'checkout'),
    ('/api/orders/checkout', 'checkout'),
    ('/api/orders/create', 'order_create'),
    ('/api/tailors/pos/customers/create', 'walk_in_create_customer'),
    ('/api/tailors/pos', 'walk_in'),
    ('/api/tailors/orders', 'tailor_fulfillment'),
    ('/api/riders/orders', 'rider_fulfillment'),
    ('/api/accounts/phone', 'auth'),
    ('/api/accounts', 'auth'),
    ('/api/orders', 'orders'),
    ('/api/tailors', 'tailors'),
    ('/api/riders', 'riders'),
    ('/api/customers', 'customers'),
    ('/api/deliveries', 'deliveries'),
    ('/api/notifications', 'notifications'),
    ('/api/finance', 'finance'),
    ('/api/customization', 'customization'),
    ('/studio/pdf-layout', 'pdf_studio'),
    ('/admin/', 'admin'),
)


def is_sentry_enabled() -> bool:
    try:
        from django.conf import settings as django_settings
        dsn = (getattr(django_settings, 'SENTRY_DSN', None) or os.getenv('SENTRY_DSN', '')).strip()
        app_env = (getattr(django_settings, 'APP_ENV', None) or os.getenv('APP_ENV', 'development')).strip().lower()
    except Exception:
        dsn = os.getenv('SENTRY_DSN', '').strip()
        app_env = os.getenv('APP_ENV', 'development').strip().lower()
    if not dsn:
        return False
    if app_env in ('staging', 'production'):
        return True
    return os.getenv('SENTRY_ENABLED', '').strip().lower() in ('1', 'true', 'yes')


def journey_for_path(path: str) -> str:
    if not path:
        return 'unknown'
    normalized = path if path.startswith('/') else f'/{path}'
    for prefix, journey in _JOURNEY_PREFIXES:
        if normalized.startswith(prefix):
            return journey
    return 'api'


def _scrub_value(key: str, value: Any) -> Any:
    if value is None:
        return value
    key_lower = str(key).lower()
    if _SENSITIVE_FIELD_RE.search(key_lower):
        return '[Filtered]'
    if isinstance(value, dict):
        return {k: _scrub_value(k, v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_scrub_value(key, item) for item in value]
    return value


def _scrub_event(event: dict, hint: dict) -> dict | None:
    request = event.get('request') or {}
    headers = request.get('headers') or {}
    if isinstance(headers, dict):
        request['headers'] = {
            k: ('[Filtered]' if str(k).lower() in _SENSITIVE_HEADERS else v)
            for k, v in headers.items()
        }
    if 'data' in request:
        request['data'] = _scrub_value('body', request.get('data'))
    event['request'] = request

    for entry in event.get('breadcrumbs', {}).get('values') or []:
        data = entry.get('data')
        if isinstance(data, dict):
            entry['data'] = _scrub_value('breadcrumb', data)

    return event


def _before_send(event: dict, hint: dict) -> dict | None:
    exc_info = hint.get('exc_info')
    if exc_info and exc_info[0] is not None:
        exc_name = f'{exc_info[0].__module__}.{exc_info[0].__name__}'
        if exc_name in _IGNORED_EXCEPTIONS:
            return None

    request = event.get('request') or {}
    url = (request.get('url') or '').lower()
    if any(url.endswith(suffix) for suffix in _IGNORED_URL_SUFFIXES):
        return None

    return _scrub_event(event, hint)


def _traces_sample_rate() -> float:
    try:
        from django.conf import settings as django_settings
        explicit = (
            getattr(django_settings, 'SENTRY_TRACES_SAMPLE_RATE', None)
            or os.getenv('SENTRY_TRACES_SAMPLE_RATE', '')
        )
        app_env = (
            getattr(django_settings, 'APP_ENV', None)
            or os.getenv('APP_ENV', 'development')
        ).strip().lower()
    except Exception:
        explicit = os.getenv('SENTRY_TRACES_SAMPLE_RATE', '').strip()
        app_env = os.getenv('APP_ENV', 'development').strip().lower()
    if explicit:
        try:
            return max(0.0, min(1.0, float(explicit)))
        except (TypeError, ValueError):
            pass
    if app_env == 'production':
        return 0.05
    if app_env == 'staging':
        return 0.1
    return 0.0


def init_sentry() -> bool:
    """Initialize Sentry once per process. Returns True when active."""
    global _sentry_initialized
    if _sentry_initialized:
        return is_sentry_enabled()
    if not is_sentry_enabled():
        return False

    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    from sentry_sdk.integrations.redis import RedisIntegration

    dsn = os.getenv('SENTRY_DSN', '').strip()
    try:
        from django.conf import settings as django_settings
        dsn = (getattr(django_settings, 'SENTRY_DSN', None) or dsn).strip()
    except Exception:
        pass
    if not dsn:
        return False

    environment = os.getenv('SENTRY_ENVIRONMENT', os.getenv('APP_ENV', 'development')).strip()
    try:
        from django.conf import settings as django_settings
        environment = (
            getattr(django_settings, 'SENTRY_ENVIRONMENT', None)
            or getattr(django_settings, 'APP_ENV', None)
            or environment
        ).strip()
    except Exception:
        pass
    release = os.getenv('SENTRY_RELEASE', os.getenv('GIT_COMMIT', '')).strip() or None
    try:
        from django.conf import settings as django_settings
        release = getattr(django_settings, 'SENTRY_RELEASE', None) or release
    except Exception:
        pass

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
            RedisIntegration(),
            LoggingIntegration(
                level=logging.INFO,
                event_level=logging.ERROR,
            ),
        ],
        traces_sample_rate=_traces_sample_rate(),
        send_default_pii=False,
        before_send=_before_send,
        max_breadcrumbs=50,
        attach_stacktrace=True,
    )
    logger.info('Sentry initialized for environment=%s', environment)
    _sentry_initialized = True
    return True


def _can_capture() -> bool:
    return _sentry_initialized


def _apply_request_scope(request, **extra) -> None:
    if not _can_capture():
        return
    import sentry_sdk

    path = getattr(request, 'path', '') or ''
    sentry_sdk.set_tag('journey', journey_for_path(path))
    sentry_sdk.set_tag('http.method', getattr(request, 'method', ''))
    for key, value in extra.items():
        if value is not None:
            sentry_sdk.set_tag(key, value)
    user = getattr(request, 'user', None)
    if user is not None and getattr(user, 'is_authenticated', False):
        sentry_sdk.set_user({
            'id': str(user.pk),
            'role': getattr(user, 'role', None),
        })


def capture_api_exception(exc: BaseException, *, request=None, **extra) -> None:
    if not _can_capture():
        return
    import sentry_sdk

    if request is not None:
        _apply_request_scope(request, **extra)
    with sentry_sdk.push_scope() as scope:
        for key, value in extra.items():
            if value is not None:
                scope.set_tag(key, value)
        sentry_sdk.capture_exception(exc)


def _sentry_level_for_status(status_code: int) -> str:
    if status_code >= 500:
        return 'error'
    if status_code >= 400:
        return 'warning'
    return 'info'


def report_api_error(
    *,
    message: str,
    request=None,
    errors=None,
    status_code: int = 500,
    exception: BaseException | None = None,
    **extra,
) -> None:
    """Report API error responses (4xx client errors and 5xx server failures)."""
    if not _can_capture() or status_code < 400:
        return
    import sentry_sdk

    if request is not None:
        _apply_request_scope(request, **extra)
    level = _sentry_level_for_status(status_code)
    error_class = 'server' if status_code >= 500 else 'client'
    with sentry_sdk.push_scope() as scope:
        scope.set_tag('api_status_code', status_code)
        scope.set_tag('api_error_class', error_class)
        for key, value in extra.items():
            if value is not None:
                scope.set_tag(key, value)
        if errors is not None:
            scope.set_extra('errors', _scrub_value('errors', errors))
        scope.set_extra('api_message', message)
        if exception is not None and status_code >= 500:
            sentry_sdk.capture_exception(exception)
        else:
            sentry_sdk.capture_message(
                message or f'API error {status_code}',
                level=level,
            )


def report_api_server_error(
    *,
    message: str,
    request=None,
    errors=None,
    status_code: int = 500,
    exception: BaseException | None = None,
    **extra,
) -> None:
    """Backward-compatible alias for server-side API failures."""
    report_api_error(
        message=message,
        request=request,
        errors=errors,
        status_code=status_code,
        exception=exception,
        **extra,
    )


def capture_task_exception(exc: BaseException, *, task_name: str = '', **extra) -> None:
    if not _can_capture():
        return
    import sentry_sdk

    with sentry_sdk.push_scope() as scope:
        scope.set_tag('journey', 'celery')
        if task_name:
            scope.set_tag('celery.task', task_name)
        for key, value in extra.items():
            if value is not None:
                scope.set_tag(key, value)
        sentry_sdk.capture_exception(exc)
