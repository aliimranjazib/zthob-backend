"""V2 business endpoints."""

from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from apps.accounts.serializers_v2 import V2BusinessSerializer, V2BusinessWriteSerializer
from apps.tailors.permissions import IsShopOwner
from apps.tailors.services.v2.business import (
    create_business,
    get_owner_business,
    update_business,
)
from apps.tailors.views.base import BaseTailorAPIView
from zthob.utils import api_response


class V2BusinessView(BaseTailorAPIView):
    permission_classes = [IsAuthenticated, IsShopOwner]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(responses={200: V2BusinessSerializer}, tags=['V2 Business'])
    def get(self, request):
        business = get_owner_business(request.user)
        if business is None:
            return api_response(
                success=False,
                message='Business not found',
                status_code=status.HTTP_404_NOT_FOUND,
                request=request,
            )
        serializer = V2BusinessSerializer(business, context={'request': request})
        return api_response(
            success=True,
            message='Business loaded',
            data=serializer.data,
            status_code=status.HTTP_200_OK,
            request=request,
        )

    @extend_schema(request=V2BusinessWriteSerializer, responses={201: V2BusinessSerializer}, tags=['V2 Business'])
    def post(self, request):
        if get_owner_business(request.user) is not None:
            return api_response(
                success=False,
                message='Business already exists',
                status_code=status.HTTP_400_BAD_REQUEST,
                request=request,
            )
        serializer = V2BusinessWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(
                success=False,
                message='Validation failed',
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
                request=request,
            )
        business = create_business(owner=request.user, validated_data=serializer.validated_data)
        response = V2BusinessSerializer(business, context={'request': request})
        return api_response(
            success=True,
            message='Business created',
            data=response.data,
            status_code=status.HTTP_201_CREATED,
            request=request,
        )

    @extend_schema(request=V2BusinessWriteSerializer, responses={200: V2BusinessSerializer}, tags=['V2 Business'])
    def patch(self, request):
        business = get_owner_business(request.user)
        if business is None:
            return api_response(
                success=False,
                message='Business not found',
                status_code=status.HTTP_404_NOT_FOUND,
                request=request,
            )
        serializer = V2BusinessWriteSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return api_response(
                success=False,
                message='Validation failed',
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
                request=request,
            )
        business = update_business(business=business, validated_data=serializer.validated_data)
        response = V2BusinessSerializer(business, context={'request': request})
        return api_response(
            success=True,
            message='Business updated',
            data=response.data,
            status_code=status.HTTP_200_OK,
            request=request,
        )
