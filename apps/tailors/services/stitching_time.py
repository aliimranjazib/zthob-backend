from django.db.models import Prefetch

from apps.orders.models import Order, OrderStatusHistory


READY_STATUSES = ('ready_for_delivery', 'ready_for_pickup')
COMPLETED_STATUSES = ('delivered', 'collected')
STITCHING_ORDER_TYPES = ('fabric_with_stitching', 'stitching_only')
SECONDS_PER_DAY = 24 * 60 * 60


def get_average_stitching_time_stats(tailor_user):
    """
    Return completed-order stitching time stats for a tailor.

    We use the first ready-for-delivery/pickup history entry as the finish point
    so rider delivery time does not inflate the tailor's stitching average.
    Older orders without history fall back to their updated_at timestamp.
    """
    if not tailor_user:
        return {
            'average_stitching_time_days': None,
            'completed_stitching_orders_count': 0,
        }

    ready_history = OrderStatusHistory.objects.filter(
        status__in=READY_STATUSES
    ).order_by('created_at')

    orders = (
        Order.objects.filter(
            tailor=tailor_user,
            order_type__in=STITCHING_ORDER_TYPES,
            status__in=COMPLETED_STATUSES,
        )
        .prefetch_related(
            Prefetch(
                'status_history',
                queryset=ready_history,
                to_attr='ready_status_history',
            )
        )
    )

    total_seconds = 0
    completed_count = 0

    for order in orders:
        ready_entry = order.ready_status_history[0] if order.ready_status_history else None
        finished_at = ready_entry.created_at if ready_entry else order.updated_at
        duration_seconds = (finished_at - order.created_at).total_seconds()

        if duration_seconds < 0:
            continue

        total_seconds += duration_seconds
        completed_count += 1

    if completed_count == 0:
        average_days = None
    else:
        average_days = round(total_seconds / completed_count / SECONDS_PER_DAY, 1)

    return {
        'average_stitching_time_days': average_days,
        'completed_stitching_orders_count': completed_count,
    }
