from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter

from apps.orders.serializers import OrderListSerializer
from apps.orders.shop_scoping import get_owner_orders_queryset, user_owns_shop_id
from apps.tailors.permissions import IsShopOwner
from apps.tailors.services.owner_reports import build_owner_reports
from apps.tailors.views.base import BaseTailorAPIView
from zthob.utils import api_response


class OwnerOrderListView(BaseTailorAPIView):
    """Cross-shop order list for the authenticated owner."""

    permission_classes = [IsAuthenticated, IsShopOwner]

    @extend_schema(
        parameters=[
            OpenApiParameter(name='shop_id', type=int, required=False),
            OpenApiParameter(name='status', type=str, required=False),
            OpenApiParameter(name='payment_status', type=str, required=False),
            OpenApiParameter(name='service_mode', type=str, required=False),
            OpenApiParameter(name='order_type', type=str, required=False),
        ],
        responses={200: OrderListSerializer(many=True)},
        tags=['Owner Orders'],
        summary='List orders across owned shops',
    )
    def get(self, request):
        shop_id = request.query_params.get('shop_id')
        if shop_id not in (None, ''):
            try:
                shop_id = int(shop_id)
            except (TypeError, ValueError):
                return api_response(
                    success=False,
                    message='Invalid shop_id',
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            if not user_owns_shop_id(request.user, shop_id):
                return api_response(
                    success=False,
                    message='Shop not found',
                    status_code=status.HTTP_404_NOT_FOUND,
                )
        else:
            shop_id = None

        orders = get_owner_orders_queryset(request.user, shop_id=shop_id).select_related(
            'customer',
            'delivery_address',
            'shop',
            'assigned_employee__user',
        ).prefetch_related(
            'order_items__fabric',
            'order_items__customer_fabric_images',
        ).order_by('-created_at')

        status_filter = request.query_params.get('status')
        if status_filter:
            orders = orders.filter(status=status_filter)

        payment_status = request.query_params.get('payment_status')
        if payment_status:
            orders = orders.filter(payment_status=payment_status)

        service_mode = request.query_params.get('service_mode')
        if service_mode:
            orders = orders.filter(service_mode=service_mode)

        order_type = request.query_params.get('order_type')
        if order_type:
            orders = orders.filter(order_type=order_type)

        serializer = OrderListSerializer(
            orders,
            many=True,
            context={'request': request, 'role': 'TAILOR'},
        )
        return api_response(
            success=True,
            message='Owner orders retrieved successfully',
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )


class OwnerOrderDetailView(BaseTailorAPIView):
    permission_classes = [IsAuthenticated, IsShopOwner]

    @extend_schema(
        responses={200: OrderListSerializer},
        tags=['Owner Orders'],
        summary='Get one order from an owned shop',
    )
    def get(self, request, order_id):
        orders = get_owner_orders_queryset(request.user).filter(id=order_id)
        order = orders.select_related(
            'customer',
            'delivery_address',
            'shop',
            'assigned_employee__user',
        ).prefetch_related(
            'order_items__fabric',
            'order_items__customer_fabric_images',
        ).first()
        if order is None:
            return api_response(
                success=False,
                message='Order not found',
                status_code=status.HTTP_404_NOT_FOUND,
            )

        from apps.orders.serializers import OrderSerializer
        serializer = OrderSerializer(order, context={'request': request, 'role': 'TAILOR'})
        return api_response(
            success=True,
            message='Order retrieved successfully',
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )


class OwnerReportsView(BaseTailorAPIView):
    permission_classes = [IsAuthenticated, IsShopOwner]

    @extend_schema(
        parameters=[
            OpenApiParameter(name='shop_id', type=int, required=False),
            OpenApiParameter(name='sales_period', type=str, required=False),
        ],
        tags=['Owner Reports'],
        summary='Owner dashboard reports across owned shops',
    )
    def get(self, request):
        shop_id = request.query_params.get('shop_id')
        if shop_id not in (None, ''):
            try:
                shop_id = int(shop_id)
            except (TypeError, ValueError):
                return api_response(
                    success=False,
                    message='Invalid shop_id',
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
        else:
            shop_id = None

        sales_period = request.query_params.get('sales_period', 'this_month')
        try:
            payload = build_owner_reports(
                request.user,
                shop_id=shop_id,
                sales_period=sales_period,
            )
        except ValueError as exc:
            return api_response(
                success=False,
                message=str(exc),
                status_code=status.HTTP_404_NOT_FOUND,
            )

        return api_response(
            success=True,
            message='Owner reports retrieved successfully',
            data=payload,
            status_code=status.HTTP_200_OK,
        )
