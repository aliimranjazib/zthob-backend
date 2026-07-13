from collections import defaultdict

from django.db.models import Q

from apps.orders.models import OrderItem
from apps.orders.serializers import format_custom_styles_for_response


def _family_member_name(item):
    if item.family_member:
        return item.family_member.name

    try:
        customer = item.order.customer
        name = customer.get_full_name() or customer.username
        return f"{name} (Self)"
    except AttributeError:
        return None


def get_customer_order_styles(owner_user, customer_ids, request=None):
    """
    Return past order styles grouped by order for each customer at this tailor shop.

    Returns:
        dict[int, list]: customer_id -> list of order style groups
    """
    if not customer_ids:
        return {}

    items = (
        OrderItem.objects.filter(
            order__tailor=owner_user,
            order__customer_id__in=customer_ids,
        )
        .exclude(Q(custom_styles__isnull=True) | Q(custom_styles=[]))
        .select_related('order', 'family_member', 'order__customer')
        .order_by('-order__created_at')
    )

    customer_orders = defaultdict(dict)

    for item in items:
        order = item.order
        customer_id = order.customer_id
        order_entry = customer_orders[customer_id].setdefault(
            order.id,
            {
                'order_id': order.id,
                'order_number': order.order_number,
                'order_date': order.created_at,
                'items': [],
            },
        )
        order_entry['items'].append({
            'item_id': item.id,
            'family_member_name': _family_member_name(item),
            'custom_styles': format_custom_styles_for_response(item.custom_styles, request),
        })

    result = {}
    for customer_id, orders_by_id in customer_orders.items():
        result[customer_id] = list(orders_by_id.values())

    return result
