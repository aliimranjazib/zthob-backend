from decimal import Decimal

from django.db.models import Count, Sum
from datetime import timedelta

from django.utils import timezone

from apps.orders.history_utils import annotate_completed_at, resolve_period_bounds
from apps.orders.models import Order

SHOP_SALES_DEFAULT_PERIOD = 'this_month'


def _money(value):
    amount = value or Decimal('0.00')
    return f'{amount.quantize(Decimal("0.01")):.2f}'


def get_shop_sales_summary(
    tailor_user,
    period=SHOP_SALES_DEFAULT_PERIOD,
    from_date=None,
    to_date=None,
    shop_id=None,
):
    """
    Aggregate walk-in shop cash collected by the tailor for a period.

    Only orders that were collected and paid at the shop are included.
    """
    start, end = resolve_period_bounds(period, from_date=from_date, to_date=to_date)

    queryset = Order.objects.filter(
        tailor=tailor_user,
        service_mode='walk_in',
        status='collected',
        payment_status='paid',
    )
    if shop_id is not None:
        queryset = queryset.filter(shop_id=shop_id)
    queryset = annotate_completed_at(queryset)
    queryset = queryset.filter(
        completed_at__gte=start,
        completed_at__lt=end,
    )

    totals = queryset.aggregate(
        orders_count=Count('id'),
        subtotal=Sum('subtotal'),
        stitching_price=Sum('stitching_price'),
        express_fee=Sum('express_fee'),
        total_collected=Sum('total_amount'),
    )

    inclusive_end = end - timedelta(microseconds=1)
    return {
        'title': 'Shop sales (Walk-in)',
        'disclaimer': 'Collected at your shop. Not included in wallet balance.',
        'period': {
            'key': period,
            'from': timezone.localdate(start).isoformat(),
            'to': timezone.localdate(inclusive_end).isoformat(),
        },
        'orders_count': totals['orders_count'] or 0,
        'total_collected': _money(totals['total_collected']),
        'breakdown': {
            'subtotal': _money(totals['subtotal']),
            'stitching_price': _money(totals['stitching_price']),
            'express_fee': _money(totals['express_fee']),
        },
    }
