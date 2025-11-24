"""
Middleware to store current request in context for automatic translation.
This allows api_response() to automatically detect language without requiring
request parameter in every view.
"""
from contextvars import ContextVar

# Context variable to store current request
_request_context: ContextVar = ContextVar('request_context', default=None)


def get_current_request():
    """
    Get the current request from context.
    Returns None if no request is available.
    """
    return _request_context.get(None)


class TranslationMiddleware:
    """
    Middleware to store request in context for automatic language detection.
    Add this to MIDDLEWARE in settings.py.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Store request in context
        _request_context.set(request)
        
        try:
            response = self.get_response(request)
        finally:
            # Clean up context after request
            _request_context.set(None)
        
        return response



