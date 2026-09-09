"""V2 shop endpoints."""

from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from apps.accounts.services.v2_auth import APP_ENTRY_OWNER, normalize_v2_app_entry
from apps.tailors.permissions import IsShopOwner
from apps.tailors.serializers.v2.shops import (
    V2ShopCreateSerializer,
    V2ShopPinSerializer,
    V2ShopSerializer,
    V2ShopUpdateSerializer,
)
from apps.tailors.services.v2.business import get_owner_business
from apps.tailors.services.v2.shops import (
    active_shops_queryset,
    build_service_area_lookup,
    get_shop_for_owner,
)
from apps.tailors.views.base import BaseTailorAPIView
from zthob.utils import api_response


def _resolve_app_entry(request) -> str:
    raw = (
        request.data.get('app_entry')
        or request.query_params.get('app_entry')
        or request.headers.get('X-App-Entry')
    )
    if raw:
        return normalize_v2_app_entry(raw) or APP_ENTRY_OWNER

    token = getattr(request, 'auth', None)
    token_entry = getattr(token, 'get', lambda _k: None)('app_entry')
    if token_entry:
        return normalize_v2_app_entry(token_entry) or APP_ENTRY_OWNER
    return APP_ENTRY_OWNER


class V2ShopListCreateView(BaseTailorAPIView):
    permission_classes = [IsAuthenticated, IsShopOwner]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(responses={200: V2ShopSerializer(many=True)}, tags=['V2 Shops'])
    def get(self, request):
        shops = active_shops_queryset(owner_id=request.user.id)
        serializer = V2ShopSerializer(
            shops,
            many=True,
            context={
                'request': request,
                'service_area_by_id': build_service_area_lookup(shops),
            },
        )
        return api_response(
            success=True,
            message='Shops fetched',
            data=serializer.data,
            status_code=status.HTTP_200_OK,
            request=request,
        )

    @extend_schema(request=V2ShopCreateSerializer, responses={201: V2ShopSerializer}, tags=['V2 Shops'])
    def post(self, request):
        app_entry = _resolve_app_entry(request)
        serializer = V2ShopCreateSerializer(
            data=request.data,
            context={
                'request': request,
                'owner': request.user,
                'business': get_owner_business(request.user),
                'app_entry': app_entry,
            },
        )
        if not serializer.is_valid():
            return api_response(
                success=False,
                message='Validation failed',
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
                request=request,
            )
        shop = serializer.save()
        shop = get_shop_for_owner(owner_id=request.user.id, shop_id=shop.id)
        response = V2ShopSerializer(
            shop,
            context={
                'request': request,
                'service_area_by_id': build_service_area_lookup([shop]),
            },
        )
        return api_response(
            success=True,
            message='Shop created',
            data=response.data,
            status_code=status.HTTP_201_CREATED,
            request=request,
        )


class V2ShopDetailView(BaseTailorAPIView):
    permission_classes = [IsAuthenticated, IsShopOwner]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def _get_shop(self, request, shop_id):
        return get_shop_for_owner(owner_id=request.user.id, shop_id=shop_id)

    @extend_schema(responses={200: V2ShopSerializer}, tags=['V2 Shops'])
    def get(self, request, shop_id):
        shop = self._get_shop(request, shop_id)
        if shop is None:
            return api_response(
                success=False,
                message='Shop not found',
                status_code=status.HTTP_404_NOT_FOUND,
                request=request,
            )
        serializer = V2ShopSerializer(
            shop,
            context={
                'request': request,
                'service_area_by_id': build_service_area_lookup([shop]),
            },
        )
        return api_response(
            success=True,
            message='Shop loaded',
            data=serializer.data,
            status_code=status.HTTP_200_OK,
            request=request,
        )

    @extend_schema(request=V2ShopUpdateSerializer, responses={200: V2ShopSerializer}, tags=['V2 Shops'])
    def patch(self, request, shop_id):
        shop = self._get_shop(request, shop_id)
        if shop is None:
            return api_response(
                success=False,
                message='Shop not found',
                status_code=status.HTTP_404_NOT_FOUND,
                request=request,
            )
        serializer = V2ShopUpdateSerializer(shop, data=request.data, partial=True)
        if not serializer.is_valid():
            return api_response(
                success=False,
                message='Validation failed',
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
                request=request,
            )
        shop = serializer.save()
        shop = get_shop_for_owner(owner_id=request.user.id, shop_id=shop.id)
        response = V2ShopSerializer(
            shop,
            context={
                'request': request,
                'service_area_by_id': build_service_area_lookup([shop]),
            },
        )
        return api_response(
            success=True,
            message='Shop updated',
            data=response.data,
            status_code=status.HTTP_200_OK,
            request=request,
        )


class V2ShopPinView(BaseTailorAPIView):
    permission_classes = [IsAuthenticated, IsShopOwner]

    @extend_schema(request=V2ShopPinSerializer, tags=['V2 Shops'])
    def patch(self, request, shop_id):
        shop = get_shop_for_owner(owner_id=request.user.id, shop_id=shop_id)
        if shop is None:
            return api_response(
                success=False,
                message='Shop not found',
                status_code=status.HTTP_404_NOT_FOUND,
                request=request,
            )
        serializer = V2ShopPinSerializer(shop, data=request.data, partial=True)
        if not serializer.is_valid():
            return api_response(
                success=False,
                message='Validation failed',
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
                request=request,
            )
        shop = serializer.save()
        return api_response(
            success=True,
            message='Shop pin updated',
            data={'id': shop.id, 'is_pinned': shop.is_pinned},
            status_code=status.HTTP_200_OK,
            request=request,
        )
