"""
Owner-side authentication endpoints.

These routes are additive. Existing /accounts/phone-verify/ behavior is unchanged
so customer, legacy tailor, rider, and staff flows keep working as before.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext as _
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.accounts.serializers import PhoneVerifySerializer, UserProfileSerializer
from apps.accounts.services.phone_verify_response import build_phone_auth_api_response
from apps.accounts.services.tailor_auth import (
    APP_ENTRY_OWNER,
    TailorSession,
    build_owner_auth_context,
    issue_tailor_tokens,
    resolve_shop_session,
    tokens_payload,
)
from apps.accounts.views import PhoneVerifyView
from zthob.utils import api_response

User = get_user_model()


class OwnerSwitchShopSerializer(serializers.Serializer):
    shop_id = serializers.IntegerField(min_value=1)


class OwnerPhoneVerifyView(PhoneVerifyView):
    """
    Owner-app OTP verify.

    Same OTP flow as phone-verify, but returns owner dashboard auth metadata.
    The generic /accounts/phone-verify/ endpoint is unchanged.
    """

    @extend_schema(
        request=PhoneVerifySerializer,
        responses={200: PhoneVerifySerializer},
        tags=['Owner Authentication'],
        summary='Verify OTP for shop owner app',
        description=(
            'Owner tailor-app login/register via OTP. Uses role=TAILOR by default '
            'and returns owner dashboard routing metadata.'
        ),
    )
    def post(self, request):
        payload = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
        payload.setdefault('role', 'TAILOR')

        serializer = PhoneVerifySerializer(data=payload)
        if not serializer.is_valid():
            return api_response(
                success=False,
                message='OTP verification failed',
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
                request=request,
            )

        user, is_new_user, error_response = self._verify_and_prepare_user(
            request,
            serializer.validated_data,
        )
        if error_response is not None:
            return error_response

        from apps.accounts.services import IdentityService

        IdentityService.ensure_profile(user, serializer.validated_data.get('role', 'TAILOR'))

        return build_phone_auth_api_response(
            request,
            user,
            is_new_user=is_new_user,
            app_entry=APP_ENTRY_OWNER,
        )


class OwnerSwitchShopView(APIView):
    """Switch the active shop session for owner or assigned staff users."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=OwnerSwitchShopSerializer,
        tags=['Owner Authentication'],
        summary='Switch active tailor shop session',
    )
    def post(self, request):
        serializer = OwnerSwitchShopSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(
                success=False,
                message='Validation failed',
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
                request=request,
            )

        shop_id = serializer.validated_data['shop_id']
        try:
            resolved = resolve_shop_session(request.user, shop_id)
        except PermissionDenied as exc:
            return api_response(
                success=False,
                message=str(exc) or _('You do not have access to this shop.'),
                status_code=status.HTTP_403_FORBIDDEN,
                request=request,
            )

        session = TailorSession(
            shop_id=resolved.shop_id,
            access_mode=resolved.access_mode,
            app_entry=APP_ENTRY_OWNER,
        )
        refresh = issue_tailor_tokens(request.user, session=session)
        tailor_context = build_owner_auth_context(request.user, app_entry=APP_ENTRY_OWNER)
        tailor_context['active_shop_id'] = session.shop_id
        tailor_context['shop_id'] = session.shop_id
        tailor_context['access_mode'] = session.access_mode
        tailor_context['routing'] = {'initial_screen': 'shop_work'}

        return api_response(
            success=True,
            message='Shop session updated successfully',
            data={
                'tokens': tokens_payload(refresh),
                'tailor_context': tailor_context,
            },
            status_code=status.HTTP_200_OK,
            request=request,
        )


class OwnerAuthContextView(APIView):
    """Return current owner auth context without issuing a new OTP."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Owner Authentication'],
        summary='Get current owner authentication context',
    )
    def get(self, request):
        user_data = UserProfileSerializer(
            request.user,
            context={'request': request, 'app_entry': APP_ENTRY_OWNER},
        ).data
        tailor_context = build_owner_auth_context(request.user, app_entry=APP_ENTRY_OWNER)

        return api_response(
            success=True,
            message='Owner auth context fetched successfully',
            data={
                'user': user_data,
                'tailor_context': tailor_context,
            },
            status_code=status.HTTP_200_OK,
            request=request,
        )
