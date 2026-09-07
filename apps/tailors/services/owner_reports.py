"""Owner dashboard reports across one or many shops."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Sum
from django.utils import timezone

from apps.finance.shop_sales import SHOP_SALES_DEFAULT_PERIOD, get_shop_sales_summary
from apps.orders.history_utils import (
    ALLOWED_PERIODS,
    annotate_completed_at,
    resolve_period_bounds,
)
from apps.orders.shop_scoping import get_owner_orders_queryset, owned_shop_ids_for_user
from apps.tailors.models import TailorProfile


def _money(value):
    amount = value or Decimal('0.00')
    return f'{amount.quantize(Decimal("0.01")):.2f}'


def _period_bounds(period, from_date=None, to_date=None):
    return resolve_period_bounds(period, from_date=from_date, to_date=to_date)


def _period_label(period, start, end):
    inclusive_end = end - timedelta(microseconds=1)
    return {
        'key': period,
        'from': timezone.localdate(start).isoformat(),
        'to': timezone.localdate(inclusive_end).isoformat(),
    }


def _order_metrics_for_period(base_orders, start, end):
    """Aggregate order counts and revenue for a period."""
    created_in_period = base_orders.filter(
        created_at__gte=start,
        created_at__lt=end,
    )
    completed_in_period = annotate_completed_at(
        base_orders.filter(status__in=['delivered', 'collected'])
    ).filter(
        completed_at__gte=start,
        completed_at__lt=end,
    )

    active_in_period = created_in_period.exclude(
        status__in=['delivered', 'collected', 'cancelled']
    )
    revenue = completed_in_period.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

    return {
        'total': created_in_period.count(),
        'completed': completed_in_period.count(),
        'active': active_in_period.count(),
        'revenue_total': revenue,
        'completed_queryset': completed_in_period,
    }


def _service_mode_analytics(completed_queryset):
    walk_in = completed_queryset.filter(service_mode='walk_in')
    home_delivery = completed_queryset.filter(service_mode='home_delivery')

    walk_in_revenue = walk_in.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    home_revenue = home_delivery.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

    return {
        'walk_in': {
            'orders_completed': walk_in.count(),
            'revenue': _money(walk_in_revenue),
        },
        'home_delivery': {
            'orders_completed': home_delivery.count(),
            'revenue': _money(home_revenue),
        },
        'combined': {
            'orders_completed': completed_queryset.count(),
            'revenue': _money(walk_in_revenue + home_revenue),
        },
    }


def build_owner_reports(
    owner_user,
    *,
    shop_id=None,
    period=SHOP_SALES_DEFAULT_PERIOD,
    from_date=None,
    to_date=None,
):
    if period not in ALLOWED_PERIODS:
        raise ValueError(
            f'Invalid period. Must be one of: {", ".join(ALLOWED_PERIODS)}.'
        )

    owned_ids = owned_shop_ids_for_user(owner_user)
    if shop_id is not None and shop_id not in owned_ids:
        raise ValueError('Shop not found for this owner.')

    start, end = _period_bounds(period, from_date=from_date, to_date=to_date)
    period_info = _period_label(period, start, end)

    shops = (
        TailorProfile.objects.filter(owner=owner_user)
        .exclude(shop_name__isnull=True)
        .exclude(shop_name='')
        .order_by('-is_pinned', '-created_at')
    )
    if shop_id is not None:
        shops = shops.filter(id=shop_id)

    per_shop = []
    aggregate_metrics = {
        'total': 0,
        'completed': 0,
        'active': 0,
        'revenue_total': Decimal('0.00'),
    }

    for shop in shops:
        shop_orders = get_owner_orders_queryset(owner_user, shop_id=shop.id)
        metrics = _order_metrics_for_period(shop_orders, start, end)
        analytics = _service_mode_analytics(metrics['completed_queryset'])

        per_shop.append({
            'shop_id': shop.id,
            'shop_name': shop.shop_name or '',
            'is_pinned': bool(shop.is_pinned),
            'period': period_info,
            'orders': {
                'total': metrics['total'],
                'completed': metrics['completed'],
                'active': metrics['active'],
            },
            'revenue': {
                'total_collected': _money(metrics['revenue_total']),
            },
            'analytics': {
                **analytics,
                'shop_sales': get_shop_sales_summary(
                    owner_user,
                    period=period,
                    from_date=from_date,
                    to_date=to_date,
                    shop_id=shop.id,
                ),
            },
        })

        aggregate_metrics['total'] += metrics['total']
        aggregate_metrics['completed'] += metrics['completed']
        aggregate_metrics['active'] += metrics['active']
        aggregate_metrics['revenue_total'] += metrics['revenue_total']

    aggregate_orders = get_owner_orders_queryset(owner_user, shop_id=shop_id)
    aggregate_completed = _order_metrics_for_period(aggregate_orders, start, end)
    summary_analytics = _service_mode_analytics(aggregate_completed['completed_queryset'])

    status_breakdown = {
        row['status']: row['count']
        for row in aggregate_orders.filter(
            created_at__gte=start,
            created_at__lt=end,
        ).values('status').annotate(count=Count('id'))
    }

    return {
        'generated_at': timezone.now().isoformat(),
        'filters': {
            'shop_id': shop_id,
            'period': period,
            'from_date': from_date,
            'to_date': to_date,
        },
        'period': period_info,
        'summary': {
            'shops_count': len(per_shop),
            'orders_total': aggregate_metrics['total'],
            'orders_completed': aggregate_metrics['completed'],
            'orders_active': aggregate_metrics['active'],
            'revenue_total': _money(aggregate_metrics['revenue_total']),
            'status_breakdown': status_breakdown,
            'analytics': summary_analytics,
        },
        'shops': per_shop,
    }
