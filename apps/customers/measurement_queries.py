"""Shared helpers for customer measurement list/detail APIs."""

from django.db.models import Q

from apps.orders.measurement_utils import has_measurement_values
from apps.orders.models import Order


def order_has_stored_measurements(order):
    """Return True when an order has any usable measurement payload."""
    if order.measurement_taken_at:
        return True
    if has_measurement_values(order.rider_measurements):
        return True
    for item in order.order_items.all():
        if has_measurement_values(item.measurements):
            return True
    return False


def get_recipient_measurements_from_order(order, recipient_type, recipient_id, user_id):
    """
    Resolve measurements for a customer or family member from order items.

    Falls back to order-level rider_measurements for customer-only orders.
    """
    if recipient_type == 'family_member':
        for item in order.order_items.all():
            if item.family_member_id == recipient_id and has_measurement_values(item.measurements):
                return item.measurements
        return None

    if recipient_type == 'customer' and recipient_id == user_id:
        for item in order.order_items.all():
            if item.family_member_id is None and has_measurement_values(item.measurements):
                return item.measurements
        if has_measurement_values(order.rider_measurements):
            return order.rider_measurements
    return None


def iter_order_recipient_measurements(order, user_id):
    """
    Yield (recipient_type, recipient_id, measurements) tuples for an order.

    Each recipient appears at most once per order.
    """
    seen = set()

    for item in order.order_items.all():
        if item.family_member_id:
            recipient_type, recipient_id = 'family_member', item.family_member_id
        else:
            recipient_type, recipient_id = 'customer', user_id

        key = (recipient_type, recipient_id)
        if key in seen:
            continue

        measurements = get_recipient_measurements_from_order(
            order,
            recipient_type,
            recipient_id,
            user_id,
        )
        if measurements:
            seen.add(key)
            yield recipient_type, recipient_id, measurements

    if not seen and has_measurement_values(order.rider_measurements):
        yield 'customer', user_id, order.rider_measurements


def customer_orders_with_measurements(customer, *, order_id=None, family_member_id=None):
    """Return customer orders that have stored measurement data."""
    queryset = Order.objects.filter(customer=customer).filter(
        Q(measurement_taken_at__isnull=False)
        | Q(rider_measurements__isnull=False)
        | Q(order_items__measurements__isnull=False)
    ).select_related(
        'customer',
        'tailor',
        'rider',
    ).prefetch_related(
        'order_items__family_member',
        'tailor__tailor_profile',
    ).distinct()

    if order_id:
        queryset = queryset.filter(id=order_id)
    if family_member_id:
        queryset = queryset.filter(order_items__family_member_id=family_member_id)

    return queryset.order_by('-measurement_taken_at', '-created_at')


def build_order_measurement_entry(order, measurements):
    """Build a single order_history entry for a recipient."""
    entry = {
        'order_id': order.id,
        'order_number': order.order_number,
        'order_type': order.order_type,
        'measurements': measurements,
        'measurement_taken_at': order.measurement_taken_at,
        'order_status': order.status,
        'rider_status': order.rider_status,
        'order_created_at': order.created_at,
        'tailor_name': None,
    }

    try:
        if order.tailor and hasattr(order.tailor, 'tailor_profile'):
            entry['tailor_name'] = order.tailor.tailor_profile.shop_name
        else:
            entry['tailor_name'] = order.tailor.username if order.tailor else None
    except Exception:
        pass

    return entry


def apply_current_measurements_fallback(recipient):
    """Use latest order history when profile measurements are missing."""
    if recipient.get('current_measurements'):
        return recipient

    history = recipient.get('order_history') or []
    if not history:
        return recipient

    latest = max(
        history,
        key=lambda entry: entry.get('measurement_taken_at') or entry.get('order_created_at'),
    )
    recipient['current_measurements'] = latest.get('measurements')
    recipient['current_measurements_note'] = 'Latest order measurements'
    return recipient
