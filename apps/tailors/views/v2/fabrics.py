"""V2 fabric catalog and analytics endpoints."""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from apps.tailors.permissions import IsShopOwner, IsShopStaff
from apps.tailors.serializers.v2.fabrics import (
    V2FabricAnalyticsQuerySerializer,
    V2FabricAssignSerializer,
    V2FabricProductSerializer,
    V2FabricProductWriteSerializer,
    V2FabricStockMovementSerializer,
    V2ShopFabricSerializer,
    V2ShopFabricUpdateSerializer,
)
from apps.tailors.services.v2.business import get_owner_business
from apps.tailors.services.v2.fabrics import (
    assign_product_to_shop,
    create_fabric_product,
    fabric_products_queryset,
    get_fabric_analytics,
    get_product_for_business,
    get_shop_fabric,
    record_stock_movement,
    shop_fabrics_queryset,
    update_fabric_product,
    update_shop_fabric,
)
from apps.tailors.services.v2.shops import get_shop_for_owner
from apps.tailors.shop_access import get_shop_staff_context
from apps.tailors.views.base import BaseTailorAPIView
from zthob.utils import api_response


def _staff_has_permission(request, permission_key: str) -> bool:
    user = request.user
    if user.is_admin:
        return True
    if get_owner_business(user) is not None:
        return True
    staff = get_shop_staff_context(user)
    if staff and staff.is_active:
        return bool(getattr(staff, permission_key, False))
    return False


class V2FabricProductListCreateView(BaseTailorAPIView):
    permission_classes = [IsAuthenticated, IsShopOwner]

    @extend_schema(responses={200: V2FabricProductSerializer(many=True)}, tags=['V2 Fabrics'])
    def get(self, request):
        business = get_owner_business(request.user)
        if business is None:
            return api_response(
                success=False,
                message='Business not found',
                status_code=status.HTTP_404_NOT_FOUND,
                request=request,
            )
        products = fabric_products_queryset(business_id=business.id)
        serializer = V2FabricProductSerializer(
            products,
            many=True,
            context={'request': request},
        )
        return api_response(
            success=True,
            message='Fabric products fetched',
            data=serializer.data,
            status_code=status.HTTP_200_OK,
            request=request,
        )

    @extend_schema(
        request=V2FabricProductWriteSerializer,
        responses={201: V2FabricProductSerializer},
        tags=['V2 Fabrics'],
    )
    def post(self, request):
        business = get_owner_business(request.user)
        if business is None:
            return api_response(
                success=False,
                message='Business not found',
                status_code=status.HTTP_404_NOT_FOUND,
                request=request,
            )
        serializer = V2FabricProductWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(
                success=False,
                message='Validation failed',
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
                request=request,
            )
        product = create_fabric_product(
            business=business,
            validated_data=serializer.validated_data,
            created_by=request.user,
        )
        product = get_product_for_business(business_id=business.id, product_id=product.id)
        response = V2FabricProductSerializer(product, context={'request': request})
        return api_response(
            success=True,
            message='Fabric product created',
            data=response.data,
            status_code=status.HTTP_201_CREATED,
            request=request,
        )


class V2FabricProductDetailView(BaseTailorAPIView):
    permission_classes = [IsAuthenticated, IsShopOwner]

    def _get_product(self, request, product_id):
        business = get_owner_business(request.user)
        if business is None:
            return None, api_response(
                success=False,
                message='Business not found',
                status_code=status.HTTP_404_NOT_FOUND,
                request=request,
            )
        product = get_product_for_business(business_id=business.id, product_id=product_id)
        if product is None:
            return None, api_response(
                success=False,
                message='Fabric product not found',
                status_code=status.HTTP_404_NOT_FOUND,
                request=request,
            )
        return product, None

    @extend_schema(responses={200: V2FabricProductSerializer}, tags=['V2 Fabrics'])
    def get(self, request, product_id):
        product, error = self._get_product(request, product_id)
        if error:
            return error
        serializer = V2FabricProductSerializer(product, context={'request': request})
        return api_response(
            success=True,
            message='Fabric product loaded',
            data=serializer.data,
            status_code=status.HTTP_200_OK,
            request=request,
        )

    @extend_schema(
        request=V2FabricProductWriteSerializer,
        responses={200: V2FabricProductSerializer},
        tags=['V2 Fabrics'],
    )
    def patch(self, request, product_id):
        product, error = self._get_product(request, product_id)
        if error:
            return error
        serializer = V2FabricProductWriteSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return api_response(
                success=False,
                message='Validation failed',
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
                request=request,
            )
        product = update_fabric_product(product=product, validated_data=serializer.validated_data)
        product = get_product_for_business(
            business_id=product.business_id,
            product_id=product.id,
        )
        response = V2FabricProductSerializer(product, context={'request': request})
        return api_response(
            success=True,
            message='Fabric product updated',
            data=response.data,
            status_code=status.HTTP_200_OK,
            request=request,
        )


class V2FabricProductAssignView(BaseTailorAPIView):
    permission_classes = [IsAuthenticated, IsShopOwner]

    @extend_schema(request=V2FabricAssignSerializer, responses={200: V2ShopFabricSerializer}, tags=['V2 Fabrics'])
    def post(self, request, product_id):
        business = get_owner_business(request.user)
        if business is None:
            return api_response(
                success=False,
                message='Business not found',
                status_code=status.HTTP_404_NOT_FOUND,
                request=request,
            )
        product = get_product_for_business(business_id=business.id, product_id=product_id)
        if product is None:
            return api_response(
                success=False,
                message='Fabric product not found',
                status_code=status.HTTP_404_NOT_FOUND,
                request=request,
            )

        serializer = V2FabricAssignSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(
                success=False,
                message='Validation failed',
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
                request=request,
            )

        shop = get_shop_for_owner(
            owner_id=request.user.id,
            shop_id=serializer.validated_data['shop_id'],
        )
        if shop is None or shop.business_id != business.id:
            return api_response(
                success=False,
                message='Shop not found',
                status_code=status.HTTP_404_NOT_FOUND,
                request=request,
            )

        shop_fabric = assign_product_to_shop(
            product=product,
            shop=shop,
            stock=serializer.validated_data['stock'],
            price_override=serializer.validated_data.get('price_override'),
            is_visible=serializer.validated_data.get('is_visible', True),
            created_by=request.user,
        )
        shop_fabric = get_shop_fabric(shop_id=shop.id, shop_fabric_id=shop_fabric.id)
        response = V2ShopFabricSerializer(shop_fabric, context={'request': request})
        return api_response(
            success=True,
            message='Fabric assigned to shop',
            data=response.data,
            status_code=status.HTTP_200_OK,
            request=request,
        )


class V2ShopFabricListView(BaseTailorAPIView):
    permission_classes = [IsAuthenticated, IsShopOwner]

    @extend_schema(responses={200: V2ShopFabricSerializer(many=True)}, tags=['V2 Fabrics'])
    def get(self, request, shop_id):
        shop = get_shop_for_owner(owner_id=request.user.id, shop_id=shop_id)
        if shop is None:
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
        if not _staff_has_permission(request, 'can_manage_catalog'):
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

        business = get_owner_business(request.user)
        if business is None or shop_fabric.shop.business_id != business.id:
            staff = get_shop_staff_context(request.user, shop_id=shop_id)
            if staff is None or staff.shop_id != shop_id:
                return api_response(
                    success=False,
                    message='Shop not found',
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
        if not _staff_has_permission(request, 'can_manage_catalog'):
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


class V2FabricAnalyticsView(BaseTailorAPIView):
    permission_classes = [IsAuthenticated, IsShopOwner]

    @extend_schema(tags=['V2 Analytics'])
    def get(self, request):
        if not _staff_has_permission(request, 'can_view_analytics'):
            return api_response(
                success=False,
                message='Permission denied',
                status_code=status.HTTP_403_FORBIDDEN,
                request=request,
            )

        business = get_owner_business(request.user)
        if business is None:
            return api_response(
                success=False,
                message='Business not found',
                status_code=status.HTTP_404_NOT_FOUND,
                request=request,
            )

        query = V2FabricAnalyticsQuerySerializer(data=request.query_params)
        if not query.is_valid():
            return api_response(
                success=False,
                message='Validation failed',
                errors=query.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
                request=request,
            )

        shop_id = query.validated_data.get('shop_id')
        if shop_id is not None:
            shop = get_shop_for_owner(owner_id=request.user.id, shop_id=shop_id)
            if shop is None or shop.business_id != business.id:
                return api_response(
                    success=False,
                    message='Shop not found',
                    status_code=status.HTTP_404_NOT_FOUND,
                    request=request,
                )

        data = get_fabric_analytics(
            business_id=business.id,
            shop_id=shop_id,
            date_from=query.validated_data.get('date_from'),
            date_to=query.validated_data.get('date_to'),
            low_stock_threshold=query.validated_data.get('low_stock_threshold', 5),
        )
        return api_response(
            success=True,
            message='Fabric analytics loaded',
            data=data,
            status_code=status.HTTP_200_OK,
            request=request,
        )
