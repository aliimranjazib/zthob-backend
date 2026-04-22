from django.db.models import Count, Prefetch, Q, F, ExpressionWrapper, FloatField
from django.db.models.functions import ACos, Cos, Radians, Sin
from django.utils import timezone
from django.core.cache import cache
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework import status

from apps.customers.models import Address
from apps.customers.serializers import (
    FabricCatalogSerializer, TailorHomeSerializer, FabricHomeSerializer,
    FabricCategorySerializer, FabricCategoryHomeSerializer, CustomerHomeSerializer
)
from apps.tailors.models import Fabric, FabricCategory, TailorProfile
from apps.core.models import Slider
from apps.core.serializers import SliderSerializer
from zthob.utils import api_response

# Riyadh city center coordinates as default launch location
RIYADH_LAT = 24.7136
RIYADH_LNG = 46.6753
DEFAULT_RADIUS = 50 # KM

class CustomerHomeAPIView(APIView):
    """
    Unified API for the Customer Home Page.
    Aggregates banners, categories, and multiple sections of tailors and fabrics.
    Defaults to Riyadh city if no location is provided. 
    Results for the default view are cached for performance.
    """
    permission_classes = [AllowAny]
    serializer_class = CustomerHomeSerializer

    @extend_schema(
        tags=["Customer Home"],
        operation_id="customer_home_data",
        description="""
        Get all data required for the customer home page. 
        Defaults to Riyadh city center if lat/lng not provided.
        """,
        parameters=[
            OpenApiParameter(name='lat', type=float, description='Latitude'),
            OpenApiParameter(name='lng', type=float, description='Longitude'),
            OpenApiParameter(name='radius', type=float, description='Search radius in Kilometers (default: 50)'),
        ],
        responses={200: CustomerHomeSerializer}
    )
    def get(self, request):
        # 1. Check for location parameters
        lat_param = request.query_params.get('lat')
        lng_param = request.query_params.get('lng')
        radius = request.query_params.get('radius', DEFAULT_RADIUS)

        # 2. Strategy: Default to Riyadh if no location provided
        is_default_view = not (lat_param and lng_param)
        
        # 3. Cache Check: If default view (Riyadh), serve from Redis if available
        if is_default_view:
            cached_data = cache.get('customer_home_default_riyadh')
            if cached_data:
                return api_response(
                    success=True,
                    message="Home page data fetched successfully (cached)",
                    data=cached_data,
                    status_code=status.HTTP_200_OK
                )

        # 4. Determine coordinates to use
        try:
            target_lat = float(lat_param) if lat_param else RIYADH_LAT
            target_lng = float(lng_param) if lng_param else RIYADH_LNG
            radius = float(radius)
        except (ValueError, TypeError):
            target_lat = RIYADH_LAT
            target_lng = RIYADH_LNG
            radius = DEFAULT_RADIUS

        now = timezone.now()
        
        # 5. Calculate Nearby Users
        # Filter addresses by distance using Haversine formula (6371 is Earth's KM radius)
        nearby_user_ids = Address.objects.annotate(
            distance=ExpressionWrapper(
                6371 * ACos(
                    Cos(Radians(target_lat)) * Cos(Radians(F('latitude'))) *
                    Cos(Radians(F('longitude')) - Radians(target_lng)) +
                    Sin(Radians(target_lat)) * Sin(Radians(F('latitude')))
                ),
                output_field=FloatField()
            )
        ).filter(distance__lte=radius).values_list('user_id', flat=True)

        # 6. Fetch Banners & Categories
        sliders = Slider.objects.filter(is_active=True).order_by('order', '-created_at')[:5]
        banners = SliderSerializer(sliders, many=True, context={'request': request}).data

        # Prefetch fabrics and their galleries to avoid N+1 queries for category images
        fabrics_prefetch = Prefetch(
            'fabrics',
            queryset=Fabric.objects.filter(is_active=True).prefetch_related('gallery').order_by('-created_at'),
            to_attr='sample_fabrics'
        )
        categories_qs = FabricCategory.objects.filter(is_active=True).prefetch_related(fabrics_prefetch).order_by('name')
        categories = FabricCategoryHomeSerializer(categories_qs, many=True, context={'request': request}).data

        # 7. Tailors Filtering (Approved & Nearby)
        active_tailors = TailorProfile.objects.filter(
            review__review_status='approved',
            shop_status=True,
            user__is_active=True,
            user_id__in=nearby_user_ids
        ).select_related('user').prefetch_related(
            'review',
            Prefetch('user__addresses', queryset=Address.objects.filter(is_default=True)),
        )

        # Build Tailors Sections using optimized serializers
        new_tailors = TailorHomeSerializer(active_tailors.order_by('-created_at')[:8], many=True, context={'request': request}).data
        top_rated_tailors = TailorHomeSerializer(active_tailors.order_by('-avg_overall_satisfaction', '-rating_count')[:8], many=True, context={'request': request}).data
        featured_tailors = TailorHomeSerializer(active_tailors.filter(is_featured=True).order_by('?')[:8], many=True, context={'request': request}).data
        most_popular_tailors = TailorHomeSerializer(active_tailors.annotate(order_count=Count('user__tailor_orders')).order_by('-order_count')[:8], many=True, context={'request': request}).data

        # 8. Fabrics Filtering (Active & Nearby)
        active_fabrics = Fabric.objects.filter(
            is_active=True,
            tailor__review__review_status='approved',
            tailor__shop_status=True,
            tailor__user__is_active=True,
            tailor__user_id__in=nearby_user_ids
        ).select_related(
            'category', 'fabric_type', 'tailor', 'tailor__user'
        ).prefetch_related('gallery', 'tags')

        # Build Fabrics Sections using optimized serializers
        flash_sale_fabrics = FabricHomeSerializer(
            active_fabrics.filter(is_on_sale=True, sale_start__lte=now, sale_end__gte=now).order_by('?')[:10], 
            many=True, context={'request': request}
        ).data
        
        new_fabrics = FabricHomeSerializer(active_fabrics.order_by('-created_at')[:10], many=True, context={'request': request}).data

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

        # 9. Store in Cache if this was the default view
        if is_default_view:
            cache.set('customer_home_default_riyadh', data, 60 * 5) # Cache for 5 mins

        return api_response(
            success=True,
            message="Home page data fetched successfully",
            data=data,
            status_code=status.HTTP_200_OK
        )
