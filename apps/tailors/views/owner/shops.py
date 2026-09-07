from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from drf_spectacular.utils import extend_schema

from apps.tailors.models import ServiceArea, TailorProfile
from apps.tailors.permissions import IsShopOwner
from apps.tailors.serializers.owner_shops import (
    OwnerShopCreateSerializer,
    OwnerShopPinSerializer,
    OwnerShopSerializer,
    OwnerShopUpdateSerializer,
)
from apps.tailors.shop_access import user_owns_shop
from apps.tailors.views.base import BaseTailorAPIView
from zthob.utils import api_response


def _owner_shop_queryset(owner):
    return (
        TailorProfile.objects.filter(owner=owner)
        .select_related('review')
        .order_by('-is_pinned', '-created_at')
    )


def _owner_shop_serializer_context(request, shops):
    if hasattr(shops, 'all'):
        shop_list = list(shops)
    elif isinstance(shops, (list, tuple)):
        shop_list = list(shops)
    else:
        shop_list = [shops]

    area_ids = set()
    for shop in shop_list:
        review = getattr(shop, 'review', None)
        if review and review.service_areas:
            area_ids.add(review.service_areas[0])

    service_area_by_id = {}
    if area_ids:
        service_area_by_id = {
            area.id: area
            for area in ServiceArea.objects.filter(id__in=area_ids)
        }

    return {
        'request': request,
        'service_area_by_id': service_area_by_id,
    }


class OwnerShopListCreateView(BaseTailorAPIView):
    """List or create shops owned by the authenticated user."""

    permission_classes = [IsAuthenticated, IsShopOwner]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(
        responses={200: OwnerShopSerializer(many=True)},
        tags=['Owner Shops'],
        summary='List shops owned by the authenticated user',
    )
    def get(self, request):
        shops = _owner_shop_queryset(request.user)
        serializer = OwnerShopSerializer(
            shops,
            many=True,
            context=_owner_shop_serializer_context(request, shops),
        )
        return api_response(
            success=True,
            message='Owned shops retrieved successfully',
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    @extend_schema(
        request=OwnerShopCreateSerializer,
        responses={201: OwnerShopSerializer},
        tags=['Owner Shops'],
        summary='Create a new shop for the authenticated owner',
    )
    def post(self, request):
        serializer = OwnerShopCreateSerializer(
            data=request.data,
            context={'request': request, 'owner': request.user},
        )
        if not serializer.is_valid():
            return api_response(
                success=False,
                message='Validation failed',
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        shop = serializer.save()
        shop = TailorProfile.objects.select_related('review').get(id=shop.id)
        response_serializer = OwnerShopSerializer(
            shop,
            context=_owner_shop_serializer_context(request, shop),
        )
        return api_response(
            success=True,
            message='Shop created successfully',
            data=response_serializer.data,
            status_code=status.HTTP_201_CREATED,
        )


class OwnerShopDetailView(BaseTailorAPIView):
    """Retrieve or update one owned shop."""

    permission_classes = [IsAuthenticated, IsShopOwner]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def _get_owned_shop(self, request, shop_id):
        try:
            shop = TailorProfile.objects.select_related('review').get(id=shop_id)
        except TailorProfile.DoesNotExist:
            return None
        if not user_owns_shop(request.user, shop):
            return None
        return shop

    @extend_schema(
        responses={200: OwnerShopSerializer},
        tags=['Owner Shops'],
        summary='Get one owned shop',
    )
    def get(self, request, shop_id):
        shop = self._get_owned_shop(request, shop_id)
        if shop is None:
            return api_response(
                success=False,
                message='Shop not found',
                status_code=status.HTTP_404_NOT_FOUND,
            )

        serializer = OwnerShopSerializer(
            shop,
            context=_owner_shop_serializer_context(request, shop),
        )
        return api_response(
            success=True,
            message='Shop retrieved successfully',
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    @extend_schema(
        request=OwnerShopUpdateSerializer,
        responses={200: OwnerShopSerializer},
        tags=['Owner Shops'],
        summary='Update one owned shop',
    )
    def patch(self, request, shop_id):
        shop = self._get_owned_shop(request, shop_id)
        if shop is None:
            return api_response(
                success=False,
                message='Shop not found',
                status_code=status.HTTP_404_NOT_FOUND,
            )

        serializer = OwnerShopUpdateSerializer(
            shop,
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
            )

        shop = serializer.save()
        shop = TailorProfile.objects.select_related('review').get(id=shop.id)
        response_serializer = OwnerShopSerializer(
            shop,
            context=_owner_shop_serializer_context(request, shop),
        )
        return api_response(
            success=True,
            message='Shop updated successfully',
            data=response_serializer.data,
            status_code=status.HTTP_200_OK,
        )


class OwnerShopPinView(BaseTailorAPIView):
    """Toggle whether a shop appears in the owner quick-access list."""

    permission_classes = [IsAuthenticated, IsShopOwner]

    @extend_schema(
        request=OwnerShopPinSerializer,
        responses={200: OwnerShopSerializer},
        tags=['Owner Shops'],
        summary='Pin or unpin an owned shop',
    )
    def patch(self, request, shop_id):
        try:
            shop = TailorProfile.objects.get(id=shop_id)
        except TailorProfile.DoesNotExist:
            return api_response(
                success=False,
                message='Shop not found',
                status_code=status.HTTP_404_NOT_FOUND,
            )

        if not user_owns_shop(request.user, shop):
            return api_response(
                success=False,
                message='Shop not found',
                status_code=status.HTTP_404_NOT_FOUND,
            )

        serializer = OwnerShopPinSerializer(shop, data=request.data, partial=True)
        if not serializer.is_valid():
            return api_response(
                success=False,
                message='Validation failed',
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        shop = serializer.save()
        shop = TailorProfile.objects.select_related('review').get(id=shop.id)
        response_serializer = OwnerShopSerializer(
            shop,
            context=_owner_shop_serializer_context(request, shop),
        )
        return api_response(
            success=True,
            message='Shop pin status updated successfully',
            data=response_serializer.data,
            status_code=status.HTTP_200_OK,
        )
