"""V2 fabric product endpoints."""

from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated

from apps.fabrics.models import FabricProduct, FabricProductImage
from apps.fabrics.permissions import staff_has_fabric_permission
from apps.fabrics.serializers.v2.products import (
    V2FabricAssignSerializer,
    V2FabricProductCreateSerializer,
    V2FabricProductSerializer,
    V2FabricProductWriteSerializer,
    V2ShopFabricSerializer,
)
from apps.fabrics.services.catalog import (
    assign_created_product_to_shop,
    create_fabric_product,
    fabric_products_queryset,
    get_product_for_business,
    pop_product_assign_fields,
    sync_product_assignments_to_legacy,
    update_fabric_product,
)
from apps.fabrics.services.images import (
    add_product_gallery_images,
    append_product_gallery_from_request,
    delete_product_image,
    parse_multipart_images,
    save_product_gallery,
    update_product_image,
    validate_gallery_images,
)
from apps.fabrics.services.listings import assign_product_to_shop, get_shop_fabric
from apps.tailors.permissions import IsShopOwner
from apps.tailors.services.v2.business import get_owner_business
from apps.tailors.services.v2.shops import get_shop_for_owner
from apps.tailors.views.base import BaseTailorAPIView
from zthob.utils import api_response


def _validation_error_response(request, exc, *, message='Validation failed'):
    errors = exc.detail if isinstance(getattr(exc, 'detail', None), (dict, list)) else {'detail': str(exc)}
    return api_response(
        success=False,
        message=message,
        errors=errors,
        status_code=status.HTTP_400_BAD_REQUEST,
        request=request,
    )


def _normalize_request_data(request):
    if request.content_type and 'multipart' in request.content_type:
        normalized = {}
        for key in request.POST:
            if key.startswith('images['):
                continue
            value = request.POST.get(key)
            if value in (None, ''):
                continue
            if key in ('is_active', 'is_on_sale', 'is_featured', 'is_visible'):
                normalized[key] = str(value).lower() == 'true'
            elif key in ('shop_id', 'stock'):
                normalized[key] = int(value)
            else:
                normalized[key] = value
        return normalized
    return request.data


class V2FabricProductListCreateView(BaseTailorAPIView):
    permission_classes = [IsAuthenticated, IsShopOwner]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

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
        request=V2FabricProductCreateSerializer,
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

        product_data, assign_data = pop_product_assign_fields(serializer.validated_data)

        from django.db import transaction

        try:
            with transaction.atomic():
                product = create_fabric_product(
                    business=business,
                    validated_data=product_data,
                    created_by=request.user,
                )
                if images:
                    save_product_gallery(product=product, images=images)
                if assign_data is not None:
                    assign_created_product_to_shop(
                        product=product,
                        owner_id=request.user.id,
                        assign_data=assign_data,
                        created_by=request.user,
                    )
        except serializers.ValidationError as exc:
            return _validation_error_response(request, exc)

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
    parser_classes = [MultiPartParser, FormParser, JSONParser]

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

        payload = _normalize_request_data(request)
        serializer = V2FabricProductWriteSerializer(data=payload, partial=True)
        if not serializer.is_valid():
            return api_response(
                success=False,
                message='Validation failed',
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
                request=request,
            )

        from django.db import transaction

        try:
            with transaction.atomic():
                product = update_fabric_product(product=product, validated_data=serializer.validated_data)
                gallery_added = append_product_gallery_from_request(product=product, request=request)
                if gallery_added:
                    sync_product_assignments_to_legacy(product=product)
        except serializers.ValidationError as exc:
            return _validation_error_response(request, exc)

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


class V2FabricProductImageAddView(BaseTailorAPIView):
    permission_classes = [IsAuthenticated, IsShopOwner]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(tags=['V2 Fabrics'])
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

        images = parse_multipart_images(request)
        try:
            validate_gallery_images(images, required=True)
            add_product_gallery_images(product=product, images=images)
        except Exception as exc:
            errors = exc.detail if hasattr(exc, 'detail') else {'images': str(exc)}
            return api_response(
                success=False,
                message='Validation failed',
                errors=errors,
                status_code=status.HTTP_400_BAD_REQUEST,
                request=request,
            )

        sync_product_assignments_to_legacy(product=product)

        product = get_product_for_business(business_id=business.id, product_id=product.id)
        response = V2FabricProductSerializer(product, context={'request': request})
        return api_response(
            success=True,
            message='Product images added',
            data=response.data,
            status_code=status.HTTP_200_OK,
            request=request,
        )


class V2FabricProductImagePrimaryView(BaseTailorAPIView):
    permission_classes = [IsAuthenticated, IsShopOwner]

    @extend_schema(tags=['V2 Fabrics'])
    def post(self, request, product_id, image_id):
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

        try:
            image = product.gallery.get(id=image_id)
        except FabricProductImage.DoesNotExist:
            return api_response(
                success=False,
                message='Image not found',
                status_code=status.HTTP_404_NOT_FOUND,
                request=request,
            )

        image.is_primary = True
        image.save()

        sync_product_assignments_to_legacy(product=product)

        product = get_product_for_business(business_id=business.id, product_id=product.id)
        response = V2FabricProductSerializer(product, context={'request': request})
        return api_response(
            success=True,
            message='Primary image updated',
            data=response.data,
            status_code=status.HTTP_200_OK,
            request=request,
        )


class V2FabricProductImageUpdateView(BaseTailorAPIView):
    permission_classes = [IsAuthenticated, IsShopOwner]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(tags=['V2 Fabrics'])
    def patch(self, request, product_id, image_id):
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

        try:
            image = product.gallery.get(id=image_id)
        except FabricProductImage.DoesNotExist:
            return api_response(
                success=False,
                message='Image not found',
                status_code=status.HTTP_404_NOT_FOUND,
                request=request,
            )

        image_file = request.FILES.get('image')
        is_primary = request.data.get('is_primary')
        order = request.data.get('order')
        try:
            update_product_image(
                image=image,
                image_file=image_file,
                is_primary=(is_primary.lower() == 'true') if isinstance(is_primary, str) else is_primary,
                order=int(order) if order is not None else None,
            )
        except Exception as exc:
            errors = exc.detail if hasattr(exc, 'detail') else {'image': str(exc)}
            return api_response(
                success=False,
                message='Validation failed',
                errors=errors,
                status_code=status.HTTP_400_BAD_REQUEST,
                request=request,
            )

        sync_product_assignments_to_legacy(product=product)

        product = get_product_for_business(business_id=business.id, product_id=product.id)
        response = V2FabricProductSerializer(product, context={'request': request})
        return api_response(
            success=True,
            message='Product image updated',
            data=response.data,
            status_code=status.HTTP_200_OK,
            request=request,
        )


class V2FabricProductImageDeleteView(BaseTailorAPIView):
    permission_classes = [IsAuthenticated, IsShopOwner]

    @extend_schema(tags=['V2 Fabrics'])
    def delete(self, request, product_id, image_id):
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

        try:
            image = product.gallery.get(id=image_id)
        except FabricProductImage.DoesNotExist:
            return api_response(
                success=False,
                message='Image not found',
                status_code=status.HTTP_404_NOT_FOUND,
                request=request,
            )

        try:
            delete_product_image(product=product, image=image)
        except Exception as exc:
            errors = exc.detail if hasattr(exc, 'detail') else {'images': str(exc)}
            return api_response(
                success=False,
                message='Validation failed',
                errors=errors,
                status_code=status.HTTP_400_BAD_REQUEST,
                request=request,
            )

        sync_product_assignments_to_legacy(product=product)

        product = get_product_for_business(business_id=business.id, product_id=product.id)
        response = V2FabricProductSerializer(product, context={'request': request})
        return api_response(
            success=True,
            message='Product image deleted',
            data=response.data,
            status_code=status.HTTP_200_OK,
            request=request,
        )
