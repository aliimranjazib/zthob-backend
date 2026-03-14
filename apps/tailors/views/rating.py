# apps/tailors/views/rating.py
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from drf_spectacular.utils import extend_schema

from apps.orders.models import Order
from apps.tailors.models import TailorProfile, TailorRating
from apps.tailors.serializers.rating import TailorRatingCreateSerializer, TailorRatingSerializer
from zthob.utils import api_response, StandardResultsSetPagination


class SubmitTailorRatingView(APIView):
    """
    POST /api/tailors/orders/{order_id}/rate/
    Customer submits a rating for a completed order. Only allowed once per order.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = TailorRatingCreateSerializer

    @extend_schema(
        tags=["Ratings"],
        operation_id="submit_tailor_rating",
        description=(
            "Submit a multi-dimensional rating for a tailor after a completed order. "
            "Only allowed for the customer who placed the order, and only when the "
            "order status is 'delivered' or 'collected'. One rating per order."
        ),
        request=TailorRatingCreateSerializer,
        responses={201: TailorRatingSerializer, 400: {}, 403: {}, 404: {}}
    )
    def post(self, request, order_id):
        # 1. Validate the order exists and belongs to this customer
        try:
            order = Order.objects.select_related('tailor__tailor_profile').get(pk=order_id)
        except Order.DoesNotExist:
            return api_response(
                success=False,
                message="Order not found",
                status_code=status.HTTP_404_NOT_FOUND
            )

        if order.customer != request.user:
            return api_response(
                success=False,
                message="You can only rate your own orders",
                status_code=status.HTTP_403_FORBIDDEN
            )

        # 2. Only allow rating on completed orders
        if order.status not in ('delivered', 'collected'):
            return api_response(
                success=False,
                message="You can only rate an order after it has been delivered or collected",
                status_code=status.HTTP_403_FORBIDDEN
            )

        # 3. No tailor assigned (e.g. measurement-only home delivery)
        if not order.tailor:
            return api_response(
                success=False,
                message="This order has no tailor to rate",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # 4. One rating per order (also enforced at DB level)
        if TailorRating.objects.filter(order=order).exists():
            return api_response(
                success=False,
                message="You have already rated this order",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # 5. Get tailor profile
        try:
            tailor_profile = order.tailor.tailor_profile
        except Exception:
            return api_response(
                success=False,
                message="Tailor profile not found",
                status_code=status.HTTP_404_NOT_FOUND
            )

        # 6. Validate and save
        serializer = TailorRatingCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(
                success=False,
                message="Invalid rating data",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        rating = serializer.save(
            order=order,
            tailor=tailor_profile,
            customer=request.user
        )

        return api_response(
            success=True,
            message="Rating submitted successfully",
            data=TailorRatingSerializer(rating).data,
            status_code=status.HTTP_201_CREATED
        )


class TailorRatingListView(APIView):
    """
    GET /api/customers/tailors/{tailor_id}/ratings/
    Returns all ratings for a specific tailor. Public endpoint.
    """
    permission_classes = [AllowAny]
    pagination_class = StandardResultsSetPagination

    @extend_schema(
        tags=["Ratings"],
        operation_id="list_tailor_ratings",
        description="Get all ratings for a specific tailor. No authentication required.",
        responses={200: TailorRatingSerializer(many=True), 404: {}}
    )
    def get(self, request, tailor_id):
        try:
            tailor_profile = TailorProfile.objects.get(user__id=tailor_id)
        except TailorProfile.DoesNotExist:
            return api_response(
                success=False,
                message="Tailor not found",
                status_code=status.HTTP_404_NOT_FOUND
            )

        ratings = TailorRating.objects.filter(
            tailor=tailor_profile
        ).select_related('customer', 'order').order_by('-created_at')

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(ratings, request)
        serializer = TailorRatingSerializer(page, many=True)

        return api_response(
            success=True,
            message="Tailor ratings fetched successfully",
            data={
                "avg_stitching_quality": tailor_profile.avg_stitching_quality,
                "avg_on_time_delivery": tailor_profile.avg_on_time_delivery,
                "avg_overall_satisfaction": tailor_profile.avg_overall_satisfaction,
                "rating_count": tailor_profile.rating_count,
                'count': paginator.page.paginator.count,
                'next': paginator.get_next_link(),
                'previous': paginator.get_previous_link(),
                'results': serializer.data
            },
            status_code=status.HTTP_200_OK
        )
