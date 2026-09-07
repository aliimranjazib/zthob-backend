"""
Owner-side session endpoints (switch shop, refresh context).

Owner/staff login uses the shared POST /accounts/phone-verify/ endpoint with
``app_entry`` set to ``owner`` or ``staff``.
"""

from __future__ import annotations

from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext as _
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.accounts.permissions import IsOwnerAppUser
from apps.accounts.serializers import UserProfileSerializer
from apps.accounts.serializers_owner import (
    OwnerProfileSerializer,
    OwnerProfileUpdateSerializer,
)
from apps.accounts.services.tailor_auth import (
    APP_ENTRY_OWNER,
    TailorSession,
    build_owner_auth_context,
    issue_tailor_tokens,
    resolve_shop_session,
    tokens_payload,
)
from zthob.utils import api_response


class OwnerSwitchShopSerializer(serializers.Serializer):
    shop_id = serializers.IntegerField(min_value=1)


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


class OwnerProfileView(APIView):
    """
    Owner personal profile (name, language, date of birth).

    Does not change phone, role, or shop data. Generic /accounts/profile/
    remains available for legacy apps.
    """

    permission_classes = [IsAuthenticated, IsOwnerAppUser]

    @extend_schema(
        responses={200: OwnerProfileSerializer},
        tags=['Owner Profile'],
        summary='Get owner personal profile',
    )
    def get(self, request):
        serializer = OwnerProfileSerializer(
            request.user,
            context={'request': request},
        )
        return api_response(
            success=True,
            message='Owner profile fetched successfully',
            data=serializer.data,
            status_code=status.HTTP_200_OK,
            request=request,
        )

    @extend_schema(
        request=OwnerProfileUpdateSerializer,
        responses={200: OwnerProfileSerializer},
        tags=['Owner Profile'],
        summary='Update owner personal profile',
    )
    def patch(self, request):
        serializer = OwnerProfileUpdateSerializer(
            request.user,
            data=request.data,
            partial=True,
            context={'request': request},
        )
        if not serializer.is_valid():
            return api_response(
                success=False,
                message='Validation failed',
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
                request=request,
            )

        user = serializer.save()
        response_serializer = OwnerProfileSerializer(
            user,
            context={'request': request},
        )
        return api_response(
            success=True,
            message='Owner profile updated successfully',
            data=response_serializer.data,
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
