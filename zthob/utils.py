from rest_framework.response import Response
from rest_framework.views import exception_handler
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework import status
from django.http import Http404
from django.core.exceptions import PermissionDenied
from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated

def api_response(*,success:bool, message:str, data:dict=None, errors:dict=None, status_code:int=200):
    return Response({
        'success':success,
        'message':message,
        'data':data,
        'error':errors
    }, status=status_code )


def custom_exception_handler(exc, context):
    """
    Custom exception handler that returns responses in the format defined by api_response
    """
    # Get the standard error response
    response = exception_handler(exc, context)
    
    if response is not None:
        # Handle JWT authentication errors
        if isinstance(exc, (InvalidToken, TokenError, AuthenticationFailed, NotAuthenticated)):
            # Provide a clean, user-friendly message
            return api_response(
                success=False,
                message="Authentication failed. Please provide a valid token.",
                errors={"detail": "Invalid or expired token"},
                status_code=response.status_code
            )
        
        # Handle permission denied errors
        elif isinstance(exc, PermissionDenied):
            return api_response(
                success=False,
                message="You do not have permission to perform this action.",
                errors={"detail": str(exc)},
                status_code=response.status_code
            )
        
        # Handle 404 errors
        elif isinstance(exc, Http404):
            return api_response(
                success=False,
                message="The requested resource was not found.",
                errors={"detail": "Not found"},
                status_code=response.status_code
            )
        
        # Handle other DRF exceptions
        else:
            # Extract error details from the response
            error_detail = response.data
            if isinstance(error_detail, dict):
                # If it's a dict, use the detail field or the whole dict
                message = error_detail.get('detail', 'An error occurred')
                errors = error_detail
            else:
                # If it's a list or other format, use it as is
                message = str(error_detail) if error_detail else 'An error occurred'
                errors = {"detail": error_detail}
            
            return api_response(
                success=False,
                message=message,
                errors=errors,
                status_code=response.status_code
            )
    
    return response