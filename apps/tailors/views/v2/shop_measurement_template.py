"""Tailor Plus per-shop measurement template customization."""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from apps.customization.serializers_shop_measurement import ShopMeasurementTemplateWriteSerializer
from apps.customization.services.shop_measurement_template import (
    replace_shop_measurement_schema,
    reset_shop_measurement_schema,
    resolve_measurement_template_for_shop,
)
from apps.fabrics.permissions import staff_has_fabric_permission, user_can_manage_shop_fabrics
from apps.tailors.permissions import IsShopStaff
from apps.tailors.services.plus_api_errors import plus_limit_api_response
from apps.tailors.services.shop_plus import TailorPlusLimitError
from apps.tailors.shop_access import get_shop_staff_context
from apps.tailors.views.base import BaseTailorAPIView
from apps.fabrics.views.v2.listings import V2ShopFabricListView
from zthob.utils import api_response


class V2ShopMeasurementTemplateView(BaseTailorAPIView):
    permission_classes = [IsAuthenticated, IsShopStaff]

    def _resolve_shop(self, request, shop_id):
        return V2ShopFabricListView()._resolve_shop(request, shop_id)

    @extend_schema(tags=['V2 Shop Measurement Template'])
    def get(self, request, shop_id):
        shop, error = self._resolve_shop(request, shop_id)
        if error:
            return error

        payload = resolve_measurement_template_for_shop(shop, request=request)
        if payload is None:
            return api_response(
                success=False,
                message='Measurement template not configured',
                status_code=status.HTTP_404_NOT_FOUND,
                request=request,
            )
        return api_response(
            success=True,
            message='Shop measurement template loaded',
            data=payload,
            status_code=status.HTTP_200_OK,
            request=request,
        )

    @extend_schema(
        request=ShopMeasurementTemplateWriteSerializer,
        tags=['V2 Shop Measurement Template'],
    )
    def put(self, request, shop_id):
        if not user_can_manage_shop_fabrics(request, shop_id=shop_id):
            staff = get_shop_staff_context(request.user, shop_id=shop_id)
            if staff is None or not staff_has_fabric_permission(request, 'can_manage_catalog'):
                return api_response(
                    success=False,
                    message='Permission denied',
                    status_code=status.HTTP_403_FORBIDDEN,
                    request=request,
                )

        shop, error = self._resolve_shop(request, shop_id)
        if error:
            return error

        serializer = ShopMeasurementTemplateWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(
                success=False,
                message='Validation failed',
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
                request=request,
            )

        try:
            replace_shop_measurement_schema(
                shop=shop,
                fields_data=serializer.validated_data['measurement_fields'],
            )
        except TailorPlusLimitError as exc:
            return plus_limit_api_response(exc, request=request)

        payload = resolve_measurement_template_for_shop(shop, request=request)
        return api_response(
            success=True,
            message='Shop measurement template saved',
            data=payload,
            status_code=status.HTTP_200_OK,
            request=request,
        )


class V2ShopMeasurementTemplateResetView(BaseTailorAPIView):
    permission_classes = [IsAuthenticated, IsShopStaff]

    @extend_schema(tags=['V2 Shop Measurement Template'])
    def post(self, request, shop_id):
        if not user_can_manage_shop_fabrics(request, shop_id=shop_id):
            return api_response(
                success=False,
                message='Permission denied',
                status_code=status.HTTP_403_FORBIDDEN,
                request=request,
            )

        shop, error = V2ShopFabricListView()._resolve_shop(request, shop_id)
        if error:
            return error

        try:
            reset_shop_measurement_schema(shop=shop)
        except TailorPlusLimitError as exc:
            return plus_limit_api_response(exc, request=request)

        payload = resolve_measurement_template_for_shop(shop, request=request)
        return api_response(
            success=True,
            message='Shop measurement template reset to platform default',
            data=payload,
            status_code=status.HTTP_200_OK,
            request=request,
        )
