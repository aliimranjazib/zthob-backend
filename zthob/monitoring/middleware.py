"""Attach Sentry request context for every API request."""

from zthob.monitoring.sentry import _apply_request_scope, is_sentry_enabled


class SentryContextMiddleware:
    """Set journey/user tags on the active Sentry scope per request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if is_sentry_enabled():
            from zthob.monitoring.sentry import _can_capture
            if _can_capture():
                _apply_request_scope(request)
        response = self.get_response(request)
        return response
