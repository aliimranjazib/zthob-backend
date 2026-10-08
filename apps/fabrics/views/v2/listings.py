"""V2 shop fabric listing endpoints."""

from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated

from apps.fabrics.permissions import staff_has_fabric_permission, user_can_manage_shop_fabrics
from apps.fabrics.serializers.v2.products import (
    V2FabricProductCreateSerializer,
    V2FabricStockMovementSerializer,
    V2ShopFabricSerializer,
    V2ShopFabricUpdateSerializer,
)
from apps.fabrics.services.catalog import create_fabric_product
from apps.fabrics.services.images import (
    parse_multipart_images,
    save_product_gallery,
    validate_gallery_images,
)
from apps.fabrics.services.listings import (
    assign_product_to_shop,
    get_shop_fabric,
    record_stock_movement,
    shop_fabrics_queryset,
    update_shop_fabric,
)
from apps.fabrics.views.v2.products import _normalize_request_data, _validation_error_response
from apps.tailors.permissions import IsShopStaff
from apps.tailors.services.v2.business import resolve_business_for_shop
from apps.tailors.services.v2.shops import get_shop_for_owner
from apps.tailors.shop_access import get_shop_staff_context
from apps.tailors.views.base import BaseTailorAPIView
from zthob.utils import api_response


class V2ShopFabricListView(BaseTailorAPIView):
    permission_classes = [IsAuthenticated, IsShopStaff]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def _resolve_shop(self, request, shop_id):
        if not user_can_manage_shop_fabrics(request, shop_id=shop_id):
            staff = get_shop_staff_context(request.user, shop_id=shop_id)
            if staff is None or not staff.is_active:
                return None, api_response(
                    success=False,
                    message='Shop not found',
                    status_code=status.HTTP_404_NOT_FOUND,
                    request=request,
                )
            if not staff_has_fabric_permission(request, 'can_manage_catalog'):
                return None, api_response(
                    success=False,
                    message='Permission denied',
                    status_code=status.HTTP_403_FORBIDDEN,
                    request=request,
                )

        shop = get_shop_for_owner(owner_id=request.user.id, shop_id=shop_id)
        if shop is None:
            staff = get_shop_staff_context(request.user, shop_id=shop_id)
            if staff is None or staff.shop_id != shop_id:
                return None, api_response(
                    success=False,
                    message='Shop not found',
                    status_code=status.HTTP_404_NOT_FOUND,
                    request=request,
                )
            shop = getattr(staff, 'shop', None) or getattr(staff, 'tailor', None)
            if shop is None:
                return None, api_response(
                    success=False,
                    message='Shop not found',
                    status_code=status.HTTP_404_NOT_FOUND,
                    request=request,
                )
        return shop, None

    @extend_schema(responses={200: V2ShopFabricSerializer(many=True)}, tags=['V2 Fabrics'])
    def get(self, request, shop_id):
        shop, error = self._resolve_shop(request, shop_id)
        if error:
            return error

        fabrics = shop_fabrics_queryset(shop_id=shop.id)
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

    @extend_schema(
        request=V2FabricProductCreateSerializer,
        responses={201: V2ShopFabricSerializer},
        tags=['V2 Fabrics'],
    )
    def post(self, request, shop_id):
        if not user_can_manage_shop_fabrics(request, shop_id=shop_id):
            return api_response(
                success=False,
                message='Permission denied',
                status_code=status.HTTP_403_FORBIDDEN,
                request=request,
            )

        shop, error = self._resolve_shop(request, shop_id)
        if error:
            return error

        payload = _normalize_request_data(request)
        images = parse_multipart_images(request)
        if images:
            try:
                validate_gallery_images(images, required=False)
            except serializers.ValidationError as exc:
                return _validation_error_response(request, exc)

        serializer = V2FabricProductCreateSerializer(data=payload)
        if not serializer.is_valid():
            return api_response(
                success=False,
                message='Validation failed',
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
                request=request,
            )

        validated_data = serializer.validated_data.copy()
        stock = validated_data.pop('default_stock', None)
        validated_data['show_in_owner_catalog'] = False

        from django.db import transaction

        with transaction.atomic():
            business = resolve_business_for_shop(shop)
            product = create_fabric_product(
                business=business,
                validated_data=validated_data,
                created_by=request.user,
            )
            if images:
                save_product_gallery(product=product, images=images)

            assign_stock = stock if stock is not None else 0
            shop_fabric = assign_product_to_shop(
                product=product,
                shop=shop,
                stock=assign_stock,
                is_visible=True,
                created_by=request.user,
            )

        shop_fabric = get_shop_fabric(shop_id=shop.id, shop_fabric_id=shop_fabric.id)
        response = V2ShopFabricSerializer(shop_fabric, context={'request': request})
        return api_response(
            success=True,
            message='Shop fabric created',
            data=response.data,
            status_code=status.HTTP_201_CREATED,
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
