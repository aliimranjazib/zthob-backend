"""Build phone verification auth responses for generic and owner tailor flows."""

from __future__ import annotations

from rest_framework import status

from apps.accounts.serializers import UserProfileSerializer
from apps.accounts.services.tailor_auth import (
    APP_ENTRY_OWNER,
    build_owner_auth_context,
    build_tailor_auth_context,
    issue_tailor_tokens,
    tokens_payload,
)
from zthob.utils import api_response


def build_phone_auth_api_response(
    request,
    user,
    *,
    is_new_user: bool,
    app_entry: str | None = None,
):
    serializer_context = {'request': request}
    if app_entry:
        serializer_context['app_entry'] = app_entry

    if app_entry == APP_ENTRY_OWNER:
        refresh = issue_tailor_tokens(user)
        user_data = UserProfileSerializer(user, context=serializer_context).data
        tailor_context = build_owner_auth_context(user, app_entry=APP_ENTRY_OWNER)
    else:
        refresh = issue_tailor_tokens(user)
        user_data = UserProfileSerializer(user, context=serializer_context).data
        tailor_context = build_tailor_auth_context(user, app_entry=app_entry)
        if app_entry is None:
            tailor_context = user_data.get('tailor_context', tailor_context)

    response_data = {
        'tokens': tokens_payload(refresh),
        'user': user_data,
        'tailor_context': tailor_context,
        'is_new_user': is_new_user,
    }

    status_code = status.HTTP_201_CREATED if is_new_user else status.HTTP_200_OK
    success_message = (
        'Registration and login successful'
        if is_new_user
        else 'Login successful'
    )

    return api_response(
        success=True,
        message=success_message,
        data=response_data,
        status_code=status_code,
        request=request,
    )
