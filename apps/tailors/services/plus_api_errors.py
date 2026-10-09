"""Map Tailor Plus limit errors to standard API responses."""

from rest_framework import status

from apps.tailors.services.shop_plus import TailorPlusLimitError
from zthob.utils import api_response


def plus_limit_api_response(exc: TailorPlusLimitError, *, request=None):
    detail = exc.detail
    if isinstance(detail, dict):
        message = detail.get('message') or 'Tailor Plus is required for this action.'
        data = {'code': 'SUBSCRIPTION_REQUIRED'}
        if detail.get('entitlement'):
            data['entitlement'] = detail['entitlement']
    else:
        message = str(detail)
        data = {'code': 'SUBSCRIPTION_REQUIRED'}
    return api_response(
        success=False,
        message=message,
        data=data,
        status_code=status.HTTP_403_FORBIDDEN,
        request=request,
    )
