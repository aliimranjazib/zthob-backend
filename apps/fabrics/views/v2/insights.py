"""Separate owner-catalog and shop-shelf fabric insight endpoints."""

from rest_framework import status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import IsAuthenticated

from apps.fabrics.permissions import (
    staff_has_fabric_permission,
    user_can_view_shop_fabric_insights,
)
from apps.fabrics.serializers.v2.insights import (
    FabricInsightWindowSerializer,
    OwnerFabricInsightQuerySerializer,
)
from apps.fabrics.services.insights import get_owner_fabric_insights, get_shop_fabric_insights
from apps.fabrics.services.insights.period import (
    InsightPeriodError,
    assert_owner_insight_window,
    assert_shop_insight_window,
    resolve_insight_window,
)
from apps.tailors.models import TailorProfile
from apps.tailors.permissions import IsShopOwner, IsShopStaff
from apps.tailors.services.plans.owner_limits import OwnerPlanLimitError
from apps.tailors.services.plus_api_errors import (
    owner_plan_limit_api_response,
    plus_limit_api_response,
)
from apps.tailors.services.shop_plus import TailorPlusLimitError
from apps.tailors.services.v2.business import get_owner_business
from apps.tailors.services.v2.shops import get_shop_for_owner
from apps.tailors.shop_access import get_shop_staff_context, user_owns_shop
from apps.tailors.views.base import BaseTailorAPIView
from zthob.utils import api_response


class V2OwnerFabricInsightsView(BaseTailorAPIView):
    permission_classes = [IsAuthenticated, IsShopOwner]

    def get(self, request):
        if not staff_has_fabric_permission(request, 'can_view_analytics'):
            return api_response(
                success=False,
                message='Permission denied',
                status_code=status.HTTP_403_FORBIDDEN,
                request=request,
            )

        query = OwnerFabricInsightQuerySerializer(data=request.query_params)
        if not query.is_valid():
            return api_response(
                success=False,
                message='Validation failed',
                errors=query.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
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

        from apps.tailors.services.plans.owner_limits import assert_owner_plus_feature

        try:
            assert_owner_plus_feature(
                owner=request.user,
                business=business,
                entitlement='fabric_inventory',
            )
        except OwnerPlanLimitError as exc:
            return owner_plan_limit_api_response(exc, request=request)

        shop_id = query.validated_data.get('shop_id')
        if shop_id is not None:
            shop = get_shop_for_owner(owner_id=request.user.id, shop_id=shop_id)
            if shop is None or (shop.business_id and shop.business_id != business.id):
                return api_response(
                    success=False,
                    message='Shop not found',
                    status_code=status.HTTP_404_NOT_FOUND,
                    request=request,
                )

        window, error = _window_or_error(
            request,
            query.validated_data,
            assert_window=lambda window: assert_owner_insight_window(
                window,
                business=business,
                owner=request.user,
            ),
            plan_response=owner_plan_limit_api_response,
            plan_error=OwnerPlanLimitError,
        )
        if error is not None:
            return error

        data = get_owner_fabric_insights(
            business=business,
            owner=request.user,
            window=window,
            shop_id=shop_id,
            low_stock_threshold=query.validated_data.get('low_stock_threshold', 5),
            top_n=query.validated_data.get('top_n', 10),
            request=request,
        )
        return api_response(
            success=True,
            message='Owner fabric insights loaded',
            data=data,
            status_code=status.HTTP_200_OK,
            request=request,
        )


class V2ShopFabricInsightsView(BaseTailorAPIView):
    permission_classes = [IsAuthenticated, IsShopStaff]
    required_employee_permissions = ('can_view_analytics', 'can_manage_catalog')

    def get(self, request, shop_id):
        shop, error = _shop_for_insights(request, shop_id)
        if error is not None:
            return error

        from apps.tailors.services.shop_plus import assert_shop_plus_feature

        try:
            assert_shop_plus_feature(shop, 'fabric_inventory')
        except TailorPlusLimitError as exc:
            return plus_limit_api_response(exc, request=request)

        query = FabricInsightWindowSerializer(data=request.query_params)
        if not query.is_valid():
            return api_response(
                success=False,
                message='Validation failed',
                errors=query.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
                request=request,
            )

        window, error = _window_or_error(
            request,
            query.validated_data,
            assert_window=lambda window: assert_shop_insight_window(window, shop=shop),
            plan_response=plus_limit_api_response,
            plan_error=TailorPlusLimitError,
        )
        if error is not None:
            return error

        data = get_shop_fabric_insights(
            shop=shop,
            window=window,
            low_stock_threshold=query.validated_data.get('low_stock_threshold', 5),
            top_n=query.validated_data.get('top_n', 10),
            request=request,
        )
        return api_response(
            success=True,
            message='Shop fabric insights loaded',
            data=data,
            status_code=status.HTTP_200_OK,
            request=request,
        )


def _window_or_error(request, params, *, assert_window, plan_response, plan_error):
    try:
        window = resolve_insight_window(
            days=params.get('days'),
            period=params.get('period'),
            date_from=params.get('date_from'),
            date_to=params.get('date_to'),
        )
        assert_window(window)
    except plan_error as exc:
        return None, plan_response(exc, request=request)
    except (InsightPeriodError, DRFValidationError, ValueError) as exc:
        message = exc.detail if isinstance(getattr(exc, 'detail', None), str) else str(exc)
        return None, api_response(
            success=False,
            message=message or 'Invalid fabric insight period',
            status_code=status.HTTP_400_BAD_REQUEST,
            request=request,
        )
    return window, None


def _shop_for_insights(request, shop_id):
    if not user_can_view_shop_fabric_insights(request, shop_id=shop_id):
        staff = get_shop_staff_context(request.user, shop_id=shop_id)
        if staff is not None and staff.is_active and staff.shop_id == shop_id:
            return None, api_response(
                success=False,
                message='Permission denied',
                status_code=status.HTTP_403_FORBIDDEN,
                request=request,
            )
        return None, api_response(
            success=False,
            message='Shop not found',
            status_code=status.HTTP_404_NOT_FOUND,
            request=request,
        )

    shop = TailorProfile.objects.filter(id=shop_id).first()
    if shop is None:
        return None, api_response(
            success=False,
            message='Shop not found',
            status_code=status.HTTP_404_NOT_FOUND,
            request=request,
        )
    if not (
        request.user.is_admin
        or user_owns_shop(request.user, shop)
        or get_shop_for_owner(owner_id=request.user.id, shop_id=shop_id) is not None
        or get_shop_staff_context(request.user, shop_id=shop_id) is not None
    ):
        return None, api_response(
            success=False,
            message='Shop not found',
            status_code=status.HTTP_404_NOT_FOUND,
            request=request,
        )
    return shop, None
