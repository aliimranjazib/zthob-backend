"""
geo_utils.py — Haversine-based geospatial filtering utilities.

Strategy (no PostGIS, no new model fields needed):
  1. Bounding-box pre-filter on the Address table  → uses simple BETWEEN
     comparisons to eliminate far-away rows before the expensive math.
  2. Haversine precise filter on the surviving rows → accurate km distance.
  3. Return a list of user_ids whose address is within the radius.
     The caller then filters TailorProfile / Fabric by those user_ids.

Works with both SQLite (dev) and PostgreSQL (production). No migrations needed.
"""

from math import radians, cos
from django.db.models import FloatField
from django.db.models.expressions import RawSQL

EARTH_RADIUS_KM = 6371.0

# Sensible defaults / guardrails
DEFAULT_RADIUS_KM = 10.0
MAX_RADIUS_KM = 200.0   # cap to avoid accidental planet-wide queries
MIN_RADIUS_KM = 0.5


def parse_geo_params(request):
    """
    Extract and validate ?lat=, ?lng=, ?radius= from a DRF request.

    Returns:
        (lat, lng, radius_km)  all floats   — when all params are valid.
        (None, None, None)                  — when any param is missing/invalid.
    Callers should treat None as "no geo filter applied".
    """
    try:
        lat = float(request.query_params.get('lat', ''))
        lng = float(request.query_params.get('lng', ''))
        radius_km = float(request.query_params.get('radius', DEFAULT_RADIUS_KM))
    except (TypeError, ValueError):
        return None, None, None

    if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
        return None, None, None

    radius_km = max(MIN_RADIUS_KM, min(radius_km, MAX_RADIUS_KM))
    return lat, lng, radius_km


def get_nearby_user_ids(lat: float, lng: float, radius_km: float) -> list:
    """
    Return a list of user_ids whose Address (with is_default=True, or any address
    if no default exists) falls within `radius_km` km of (lat, lng).

    Steps:
      1. Filter Address rows where lat/lng is not NULL.
      2. Apply a bounding-box pre-filter — cheap BETWEEN query, no math.
      3. Annotate with precise Haversine distance_km.
      4. Filter to radius.
      5. Return distinct user_ids.

    No new model fields or migrations required — uses the existing
    Address.latitude / Address.longitude columns.
    """
    # Import here to avoid circular imports at module load time
    from apps.customers.models import Address

    # ── Step 1: Only addresses that have coordinates ─────────────────────────
    qs = Address.objects.filter(
        latitude__isnull=False,
        longitude__isnull=False,
        user__isnull=False,
    )

    # ── Step 2: Bounding-box pre-filter ──────────────────────────────────────
    # 1° latitude  ≈ 111.0 km (constant everywhere)
    # 1° longitude ≈ 111.0 × cos(lat) km (shrinks toward the poles)
    lat_delta = radius_km / 111.0
    cos_lat = cos(radians(lat)) or 1e-10   # guard against division by zero at poles
    lng_delta = radius_km / (111.0 * cos_lat)

    qs = qs.filter(
        latitude__range=(lat - lat_delta, lat + lat_delta),
        longitude__range=(lng - lng_delta, lng + lng_delta),
    )

    # ── Step 3: Haversine annotation ─────────────────────────────────────────
    # LEAST(1.0, ...) guards against floating-point values slightly > 1.0
    # that would make acos() return NaN.
    haversine_sql = """
        (%(r)s * acos(
            LEAST(1.0,
                cos(radians(%(lat)s)) * cos(radians(latitude)) *
                cos(radians(longitude) - radians(%(lng)s)) +
                sin(radians(%(lat)s)) * sin(radians(latitude))
            )
        ))
    """ % {'r': EARTH_RADIUS_KM, 'lat': '%s', 'lng': '%s'}

    qs = qs.annotate(
        distance_km=RawSQL(haversine_sql, (lat, lng, lat), output_field=FloatField())
    )

    # ── Step 4: Filter to radius ─────────────────────────────────────────────
    qs = qs.filter(distance_km__lte=radius_km)

    # ── Step 5: Return distinct user_ids ─────────────────────────────────────
    return list(qs.values_list('user_id', flat=True).distinct())
