from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from drf_spectacular.utils import extend_schema

from apps.tailors.models import TailorProfile
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
        shops = (
            TailorProfile.objects.filter(owner=request.user)
            .order_by('-is_pinned', '-created_at')
        )
        serializer = OwnerShopSerializer(
            shops,
            many=True,
            context={'request': request},
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
        response_serializer = OwnerShopSerializer(shop, context={'request': request})
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
            shop = TailorProfile.objects.get(id=shop_id)
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

        serializer = OwnerShopSerializer(shop, context={'request': request})
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
        response_serializer = OwnerShopSerializer(shop, context={'request': request})
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
        response_serializer = OwnerShopSerializer(shop, context={'request': request})
        return api_response(
            success=True,
            message='Shop pin status updated successfully',
            data=response_serializer.data,
            status_code=status.HTTP_200_OK,
        )
