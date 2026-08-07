"""Shared tailor section rules for customer home previews and paginated See All lists."""

from django.db.models import Count, F, FloatField, Prefetch, ExpressionWrapper
from django.db.models.functions import ACos, Cos, Radians, Sin

from apps.customers.models import Address
from apps.tailors.models import TailorProfile
from zthob.geo_utils import MAX_RADIUS_KM, MIN_RADIUS_KM

TAILOR_SECTIONS = (
    'featured',
    'express_delivery',
    'most_popular',
    'new',
    'top_rated',
)

HOME_DEFAULT_RADIUS_KM = 50.0


def is_valid_tailor_section(section: str) -> bool:
    return section in TAILOR_SECTIONS


def allowed_tailor_sections_display() -> str:
    return ', '.join(TAILOR_SECTIONS)


def get_home_nearby_user_ids(lat: float, lng: float, radius_km: float) -> list:
    """Same Haversine filter used by CustomerHomeAPIView."""
    return list(
        Address.objects.annotate(
            distance=ExpressionWrapper(
                6371 * ACos(
                    Cos(Radians(lat)) * Cos(Radians(F('latitude'))) *
                    Cos(Radians(F('longitude')) - Radians(lng)) +
                    Sin(Radians(lat)) * Sin(Radians(F('latitude')))
                ),
                output_field=FloatField()
            )
        ).filter(distance__lte=radius_km).values_list('user_id', flat=True)
    )


def parse_section_geo_params(request):
    """
    Parse lat/lng/radius for paginated section list requests.

    Returns:
        (nearby_user_ids, geo_applied)
        - geo_applied=False → national/unfiltered list for the section
        - geo_applied=True  → nearby_user_ids from the same Haversine logic as home
    """
    lat_param = request.query_params.get('lat')
    lng_param = request.query_params.get('lng')
    if not (lat_param and lng_param):
        return None, False

    try:
        lat = float(lat_param)
        lng = float(lng_param)
        radius_km = float(request.query_params.get('radius', HOME_DEFAULT_RADIUS_KM))
    except (TypeError, ValueError):
        return None, False

    if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
        return None, False

    radius_km = max(MIN_RADIUS_KM, min(radius_km, MAX_RADIUS_KM))
    return get_home_nearby_user_ids(lat, lng, radius_km), True


def get_active_tailors_queryset(*, nearby_user_ids=None):
    """Base queryset shared by home previews and section list endpoints."""
    queryset = TailorProfile.objects.filter(
        review__review_status='approved',
        shop_status=True,
        user__is_active=True,
    ).select_related('user').prefetch_related(
        'review',
        Prefetch('user__addresses', queryset=Address.objects.filter(is_default=True)),
    )
    if nearby_user_ids is not None:
        queryset = queryset.filter(user_id__in=nearby_user_ids)
    return queryset


def apply_tailor_section(queryset, section: str):
    """Apply the same filter/sort rules used by customer home preview arrays."""
    if section == 'new':
        return queryset.order_by('-created_at')
    if section == 'top_rated':
        return queryset.order_by('-avg_overall_satisfaction', '-rating_count')
    if section == 'featured':
        return queryset.filter(is_featured=True).order_by('-avg_overall_satisfaction')
    if section == 'express_delivery':
        return queryset.filter(is_express_delivery_enabled=True).order_by('-avg_overall_satisfaction')
    if section == 'most_popular':
        return queryset.annotate(order_count=Count('user__tailor_orders')).order_by('-order_count')
    return queryset
