"""Walk-in measurements reusable at checkout for Tailor Plus shops (not shown in library)."""

from __future__ import annotations

from apps.customers.models import FamilyMember
from apps.orders.measurement_utils import has_measurement_values, public_measurements
from apps.orders.models import Order
from apps.tailors.services.shop_plus import is_shop_plus_active


def _latest_walk_in_measurements(*, customer, shop_id: int, family_member_id=None):
    queryset = (
        Order.objects.filter(
            customer=customer,
            shop_id=shop_id,
            service_mode='walk_in',
        )
        .prefetch_related('order_items__family_member')
        .order_by('-measurement_taken_at', '-created_at')
    )
    for order in queryset:
        for item in order.order_items.all():
            if family_member_id is None:
                if item.family_member_id is not None:
                    continue
            elif item.family_member_id != family_member_id:
                continue
            if not has_measurement_values(item.measurements):
                continue
            return {
                'measurements': public_measurements(item.measurements),
                'source_order_id': order.id,
                'order_number': order.order_number,
                'measurement_taken_at': (
                    order.measurement_taken_at.isoformat()
                    if order.measurement_taken_at
                    else None
                ),
            }
    return None


def build_shop_reusable_measurements_payload(*, customer, shop) -> dict:
    if not is_shop_plus_active(shop):
        return {
            'shop_id': shop.id,
            'is_tailor_plus': False,
            'customer': None,
            'family_members': [],
        }

    family_members = FamilyMember.objects.filter(user=customer).order_by('name', 'id')
    family_payload = []
    for member in family_members:
        entry = _latest_walk_in_measurements(
            customer=customer,
            shop_id=shop.id,
            family_member_id=member.id,
        )
        if entry:
            family_payload.append({'family_member_id': member.id, **entry})

    return {
        'shop_id': shop.id,
        'is_tailor_plus': True,
        'customer': _latest_walk_in_measurements(
            customer=customer,
            shop_id=shop.id,
            family_member_id=None,
        ),
        'family_members': family_payload,
    }
