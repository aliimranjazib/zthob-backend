"""V2 shop query helpers with prefetch to avoid N+1."""

from __future__ import annotations

from apps.tailors.models import ServiceArea, TailorProfile


def active_shops_queryset(*, owner_id: int | None = None, business_id: int | None = None):
    qs = TailorProfile.objects.select_related('review', 'business').order_by(
        '-is_pinned',
        '-created_at',
    )
    if owner_id is not None:
        qs = qs.filter(owner_id=owner_id)
    if business_id is not None:
        qs = qs.filter(business_id=business_id)
    return qs.exclude(shop_name__isnull=True).exclude(shop_name='')


def build_service_area_lookup(shops) -> dict[int, ServiceArea]:
    area_ids = set()
    shop_list = list(shops)
    for shop in shop_list:
        review = getattr(shop, 'review', None)
        if review and review.service_areas:
            area_ids.add(review.service_areas[0])
    if not area_ids:
        return {}
    return {
        area.id: area
        for area in ServiceArea.objects.filter(id__in=area_ids)
    }


def get_shop_for_owner(*, owner_id: int, shop_id: int) -> TailorProfile | None:
    return (
        active_shops_queryset(owner_id=owner_id)
        .filter(id=shop_id)
        .first()
    )
