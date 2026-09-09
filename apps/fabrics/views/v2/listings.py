"""V2 shop fabric listing endpoints."""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from apps.fabrics.permissions import staff_has_fabric_permission, user_can_manage_shop_fabrics
from apps.fabrics.serializers.v2.products import (
    V2FabricStockMovementSerializer,
    V2ShopFabricSerializer,
    V2ShopFabricUpdateSerializer,
)
from apps.fabrics.services.listings import (
    get_shop_fabric,
    record_stock_movement,
    shop_fabrics_queryset,
    update_shop_fabric,
)
from apps.tailors.permissions import IsShopOwner, IsShopStaff
from apps.tailors.services.v2.business import get_owner_business
from apps.tailors.services.v2.shops import get_shop_for_owner
from apps.tailors.shop_access import get_shop_staff_context
from apps.tailors.views.base import BaseTailorAPIView
from zthob.utils import api_response


class V2ShopFabricListView(BaseTailorAPIView):
    permission_classes = [IsAuthenticated, IsShopStaff]

    @extend_schema(responses={200: V2ShopFabricSerializer(many=True)}, tags=['V2 Fabrics'])
    def get(self, request, shop_id):
        if not user_can_manage_shop_fabrics(request, shop_id=shop_id):
            staff = get_shop_staff_context(request.user, shop_id=shop_id)
            if staff is None or not staff.is_active:
                return api_response(
                    success=False,
                    message='Shop not found',
                    status_code=status.HTTP_404_NOT_FOUND,
                    request=request,
                )
            if not staff_has_fabric_permission(request, 'can_manage_catalog'):
                return api_response(
                    success=False,
                    message='Permission denied',
                    status_code=status.HTTP_403_FORBIDDEN,
                    request=request,
                )

        shop = get_shop_for_owner(owner_id=request.user.id, shop_id=shop_id)
        if shop is None:
            staff = get_shop_staff_context(request.user, shop_id=shop_id)
            if staff is None or staff.shop_id != shop_id:
                return api_response(
                    success=False,
                    message='Shop not found',
                    status_code=status.HTTP_404_NOT_FOUND,
                    request=request,
                )

        fabrics = shop_fabrics_queryset(shop_id=shop_id)
        serializer = V2ShopFabricSerializer(
            fabrics,
            many=True,
            context={'request': request},
        )
        return api_response(
            success=True,
            message='Shop fabrics fetched',
            data=serializer.data,
            status_code=status.HTTP_200_OK,
            request=request,
        )


class V2ShopFabricDetailView(BaseTailorAPIView):
    permission_classes = [IsAuthenticated, IsShopStaff]
    required_employee_permission = 'can_manage_catalog'

    @extend_schema(
        request=V2ShopFabricUpdateSerializer,
        responses={200: V2ShopFabricSerializer},
        tags=['V2 Fabrics'],
    )
    def patch(self, request, shop_id, shop_fabric_id):
        if not user_can_manage_shop_fabrics(request, shop_id=shop_id):
            return api_response(
                success=False,
                message='Permission denied',
                status_code=status.HTTP_403_FORBIDDEN,
                request=request,
            )

        shop_fabric = get_shop_fabric(shop_id=shop_id, shop_fabric_id=shop_fabric_id)
        if shop_fabric is None:
            return api_response(
                success=False,
                message='Shop fabric not found',
                status_code=status.HTTP_404_NOT_FOUND,
                request=request,
            )

        serializer = V2ShopFabricUpdateSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return api_response(
                success=False,
                message='Validation failed',
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
                request=request,
            )
        shop_fabric = update_shop_fabric(
            shop_fabric=shop_fabric,
            validated_data=serializer.validated_data,
        )
        shop_fabric = get_shop_fabric(shop_id=shop_id, shop_fabric_id=shop_fabric.id)
        response = V2ShopFabricSerializer(shop_fabric, context={'request': request})
        return api_response(
            success=True,
            message='Shop fabric updated',
            data=response.data,
            status_code=status.HTTP_200_OK,
            request=request,
        )


class V2ShopFabricStockMovementView(BaseTailorAPIView):
    permission_classes = [IsAuthenticated, IsShopStaff]
    required_employee_permission = 'can_manage_catalog'

    @extend_schema(
        request=V2FabricStockMovementSerializer,
        responses={200: V2ShopFabricSerializer},
        tags=['V2 Fabrics'],
    )
    def post(self, request, shop_id, shop_fabric_id):
        if not user_can_manage_shop_fabrics(request, shop_id=shop_id):
            return api_response(
                success=False,
                message='Permission denied',
                status_code=status.HTTP_403_FORBIDDEN,
                request=request,
            )

        shop_fabric = get_shop_fabric(shop_id=shop_id, shop_fabric_id=shop_fabric_id)
        if shop_fabric is None:
            return api_response(
                success=False,
                message='Shop fabric not found',
                status_code=status.HTTP_404_NOT_FOUND,
                request=request,
            )

        serializer = V2FabricStockMovementSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(
                success=False,
                message='Validation failed',
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
                request=request,
            )

        shop_fabric = record_stock_movement(
            shop_fabric=shop_fabric,
            movement_type=serializer.validated_data['movement_type'],
            quantity=serializer.validated_data['quantity'],
            reason=serializer.validated_data.get('reason', ''),
            note=serializer.validated_data.get('note', ''),
            created_by=request.user,
        )
        shop_fabric = get_shop_fabric(shop_id=shop_id, shop_fabric_id=shop_fabric.id)
        response = V2ShopFabricSerializer(shop_fabric, context={'request': request})
        return api_response(
            success=True,
            message='Stock updated',
            data=response.data,
            status_code=status.HTTP_200_OK,
            request=request,
        )
