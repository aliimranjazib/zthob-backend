from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework import status
from django.db.models import Count, Prefetch
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from drf_spectacular.utils import extend_schema

from apps.customers.models import Address
from apps.customers.serializers import (
    FabricCatalogSerializer, TailorProfileSerializer, 
    FabricCategorySerializer, CustomerHomeSerializer
)
from apps.tailors.models import Fabric, FabricCategory, TailorProfile
from apps.core.models import Slider
from apps.core.serializers import SliderSerializer
from zthob.utils import api_response

class CustomerHomeAPIView(APIView):
    """
    Unified API for the Customer Home Page.
    Aggregates banners, categories, and multiple sections of tailors and fabrics.
    """
    permission_classes = [AllowAny]
    serializer_class = CustomerHomeSerializer

    @method_decorator(cache_page(60 * 5))  # Cache for 5 minutes
    @extend_schema(
        tags=["Customer Home"],
        operation_id="customer_home_data",
        description="Get all data required for the customer home page in a single call. Cached for 5 minutes.",
        responses={200: CustomerHomeSerializer}
    )
    def get(self, request):
        now = timezone.now()

        # 1. Banners
        sliders = Slider.objects.filter(is_active=True).order_by('order', '-created_at')[:5]
        banners = SliderSerializer(sliders, many=True, context={'request': request}).data

        # 2. Categories
        categories_qs = FabricCategory.objects.filter(is_active=True).order_by('name')
        categories = FabricCategorySerializer(categories_qs, many=True, context={'request': request}).data

        # Base filters for active approved tailors
        active_tailors = TailorProfile.objects.filter(
            review__review_status='approved',
            shop_status=True,
            user__is_active=True
        ).select_related('user').prefetch_related(
            'review',
            Prefetch('user__addresses', queryset=Address.objects.filter(is_default=True)),
        )

        # 3. New Tailors
        new_tailors_qs = active_tailors.order_by('-created_at')[:8]
        new_tailors = TailorProfileSerializer(new_tailors_qs, many=True, context={'request': request}).data

        # 4. Top Rated Tailors
        top_rated_qs = active_tailors.order_by('-avg_overall_satisfaction', '-rating_count')[:8]
        top_rated_tailors = TailorProfileSerializer(top_rated_qs, many=True, context={'request': request}).data

        # 5. Featured Tailors
        featured_tailors_qs = active_tailors.filter(is_featured=True).order_by('?')[:8]
        featured_tailors = TailorProfileSerializer(featured_tailors_qs, many=True, context={'request': request}).data

        # 6. Most Popular Tailors
        popular_tailors_qs = active_tailors.annotate(
            order_count=Count('user__tailor_orders')
        ).order_by('-order_count')[:8]
        most_popular_tailors = TailorProfileSerializer(popular_tailors_qs, many=True, context={'request': request}).data

        # Base filters for active fabrics
        active_fabrics = Fabric.objects.filter(
            is_active=True,
            tailor__review__review_status='approved',
            tailor__shop_status=True,
            tailor__user__is_active=True
        ).select_related(
            'category', 'fabric_type', 'tailor', 'tailor__user'
        ).prefetch_related('gallery', 'tags')

        # 7. Flash Sale Fabrics (ONLY active sales - time bound)
        flash_sale_qs = active_fabrics.filter(
            is_on_sale=True,
            sale_start__lte=now,
            sale_end__gte=now
        ).order_by('?')[:10]
        flash_sale_fabrics = FabricCatalogSerializer(flash_sale_qs, many=True, context={'request': request}).data

        # 8. New Fabrics
        new_fabrics_qs = active_fabrics.order_by('-created_at')[:10]
        new_fabrics = FabricCatalogSerializer(new_fabrics_qs, many=True, context={'request': request}).data

        data = {
            "banners": banners,
            "categories": categories,
            "new_tailors": new_tailors,
            "top_rated_tailors": top_rated_tailors,
            "most_popular_tailors": most_popular_tailors,
            "featured_tailors": featured_tailors,
            "flash_sale_fabrics": flash_sale_fabrics,
            "new_fabrics": new_fabrics,
        }

        return api_response(
            success=True,
            message="Home page data fetched successfully",
            data=data,
            status_code=status.HTTP_200_OK
        )
