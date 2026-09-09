"""V2 authentication endpoints."""

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from apps.accounts.serializers_v2 import (
    V2PhoneVerifySerializer,
    V2ProfileSerializer,
    V2SwitchShopSerializer,
)
from apps.accounts.services.v2_auth import (
    build_v2_me_payload,
    build_v2_profile_payload,
    build_v2_verify_payload,
    switch_shop_session,
    validate_app_entry_for_user,
)
from apps.accounts.views import PhoneLoginView, PhoneVerifyView
from zthob.utils import api_response


class V2PhoneLoginView(PhoneLoginView):
    """Send OTP — reuses v1 phone-login implementation."""


class V2PhoneVerifyView(PhoneVerifyView):
    """Verify OTP and return slim v2 auth payload."""

    @extend_schema(
        request=V2PhoneVerifySerializer,
        tags=['V2 Auth'],
        summary='Verify OTP (v2 slim response)',
    )
    def post(self, request):
        serializer = V2PhoneVerifySerializer(data=request.data)
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

        role = serializer.validated_data.get('role', 'USER')
        app_entry = serializer.validated_data.get('app_entry')

        from apps.accounts.services import IdentityService
        IdentityService.ensure_profile(user, role)

        try:
            validate_app_entry_for_user(user, app_entry)
        except Exception as exc:
            from rest_framework.exceptions import PermissionDenied
            if isinstance(exc, PermissionDenied):
                return api_response(
                    success=False,
                    message=str(exc.detail if hasattr(exc, 'detail') else exc),
                    status_code=status.HTTP_403_FORBIDDEN,
                    request=request,
                )
            raise

        payload = build_v2_verify_payload(
            user,
            app_entry=app_entry,
            is_new_user=is_new_user,
        )
        status_code = status.HTTP_201_CREATED if is_new_user else status.HTTP_200_OK
        message = (
            'Registration and login successful'
            if is_new_user
            else 'Login successful'
        )
        return api_response(
            success=True,
            message=message,
            data=payload,
            status_code=status_code,
            request=request,
        )


class V2MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['V2 Auth'], summary='Load account context for current session')
    def get(self, request):
        app_entry = request.query_params.get('app_entry') or request.headers.get('X-App-Entry')
        try:
            data = build_v2_me_payload(request.user, app_entry=app_entry)
        except Exception as exc:
            from rest_framework.exceptions import PermissionDenied
            if isinstance(exc, PermissionDenied):
                return api_response(
                    success=False,
                    message=str(exc.detail if hasattr(exc, 'detail') else exc),
                    status_code=status.HTTP_403_FORBIDDEN,
                    request=request,
                )
            raise
        return api_response(
            success=True,
            message='Account loaded',
            data=data,
            status_code=status.HTTP_200_OK,
            request=request,
        )


class V2ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['V2 Auth'], summary='Get personal profile')
    def get(self, request):
        return api_response(
            success=True,
            message='Profile loaded',
            data=build_v2_profile_payload(request.user),
            status_code=status.HTTP_200_OK,
            request=request,
        )

    @extend_schema(request=V2ProfileSerializer, tags=['V2 Auth'], summary='Update personal profile')
    def patch(self, request):
        serializer = V2ProfileSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return api_response(
                success=False,
                message='Validation failed',
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
                request=request,
            )

        user = request.user
        full_name = serializer.validated_data.get('full_name')
        if full_name is not None:
            parts = full_name.strip().split(' ', 1)
            user.first_name = parts[0]
            user.last_name = parts[1] if len(parts) > 1 else ''
        if 'language' in serializer.validated_data:
            user.language = serializer.validated_data['language']
        user.save()
        return api_response(
            success=True,
            message='Profile updated',
            data=build_v2_profile_payload(user),
            status_code=status.HTTP_200_OK,
            request=request,
        )


class V2SwitchShopView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=V2SwitchShopSerializer, tags=['V2 Auth'], summary='Switch active shop')
    def post(self, request):
        serializer = V2SwitchShopSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(
                success=False,
                message='Validation failed',
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
                request=request,
            )

        shop_id = serializer.validated_data['shop_id']
        app_entry = serializer.validated_data.get('app_entry')
        try:
            data = switch_shop_session(
                request.user,
                shop_id,
                app_entry=app_entry,
            )
        except Exception as exc:
            from rest_framework.exceptions import PermissionDenied
            if isinstance(exc, PermissionDenied):
                return api_response(
                    success=False,
                    message=str(exc.detail if hasattr(exc, 'detail') else exc),
                    status_code=status.HTTP_403_FORBIDDEN,
                    request=request,
                )
            raise

        return api_response(
            success=True,
            message='Shop switched successfully',
            data=data,
            status_code=status.HTTP_200_OK,
            request=request,
        )
