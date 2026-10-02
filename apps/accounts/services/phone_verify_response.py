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


def resolve_phone_verify_app_entry(
    user,
    app_entry: str | None,
    *,
    is_new_user: bool,
) -> tuple[str | None, str | None]:
    """
    Use explicit app_entry when provided; for returning users infer from platform identity.
    """
    from apps.accounts.services.v2_auth import (
        infer_app_entry_for_user,
        resolve_membership_type,
        validate_app_entry_for_user,
    )

    if app_entry:
        validated = validate_app_entry_for_user(user, app_entry)
        return validated, 'request'
    if is_new_user:
        return None, None

    if resolve_membership_type(user) == 'none':
        return None, None

    inferred = infer_app_entry_for_user(user)
    validated = validate_app_entry_for_user(user, inferred)
    return validated, 'inferred'


def build_phone_auth_api_response(
    request,
    user,
    *,
    is_new_user: bool,
    app_entry: str | None = None,
):
    resolved_app_entry, app_entry_source = resolve_phone_verify_app_entry(
        user,
        app_entry,
        is_new_user=is_new_user,
    )

    serializer_context = {'request': request}
    if resolved_app_entry:
        serializer_context['app_entry'] = resolved_app_entry

    if resolved_app_entry == APP_ENTRY_OWNER:
        refresh = issue_tailor_tokens(user)
        user_data = UserProfileSerializer(user, context=serializer_context).data
        tailor_context = build_owner_auth_context(user, app_entry=APP_ENTRY_OWNER)
    else:
        refresh = issue_tailor_tokens(user)
        user_data = UserProfileSerializer(user, context=serializer_context).data
        tailor_context = build_tailor_auth_context(user, app_entry=resolved_app_entry)
        if resolved_app_entry is None:
            tailor_context = user_data.get('tailor_context', tailor_context)

    response_data = {
        'tokens': tokens_payload(refresh),
        'user': user_data,
        'tailor_context': tailor_context,
        'is_new_user': is_new_user,
    }
    if resolved_app_entry:
        response_data['app_entry'] = resolved_app_entry
    if app_entry_source:
        response_data['app_entry_source'] = app_entry_source

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
