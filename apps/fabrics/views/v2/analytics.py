"""V2 fabric analytics endpoints."""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from apps.fabrics.permissions import staff_has_fabric_permission
from apps.fabrics.serializers.v2.products import V2FabricAnalyticsQuerySerializer
from apps.fabrics.services.analytics import get_fabric_analytics
from apps.tailors.permissions import IsShopOwner
from apps.tailors.services.v2.business import get_owner_business
from apps.tailors.services.v2.shops import get_shop_for_owner
from apps.tailors.views.base import BaseTailorAPIView
from zthob.utils import api_response


class V2FabricAnalyticsView(BaseTailorAPIView):
    permission_classes = [IsAuthenticated, IsShopOwner]

    @extend_schema(tags=['V2 Analytics'])
    def get(self, request):
        if not staff_has_fabric_permission(request, 'can_view_analytics'):
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
