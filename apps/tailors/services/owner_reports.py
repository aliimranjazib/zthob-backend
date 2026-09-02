"""Owner dashboard reports across one or many shops."""

from __future__ import annotations

from decimal import Decimal

from django.db.models import Count, Sum
from django.utils import timezone

from apps.finance.shop_sales import SHOP_SALES_DEFAULT_PERIOD, get_shop_sales_summary
from apps.orders.shop_scoping import get_owner_orders_queryset, owned_shop_ids_for_user
from apps.tailors.models import TailorProfile


def _money(value):
    amount = value or Decimal('0.00')
    return f'{amount.quantize(Decimal("0.01")):.2f}'


def build_owner_reports(owner_user, *, shop_id=None, sales_period=SHOP_SALES_DEFAULT_PERIOD):
    owned_ids = owned_shop_ids_for_user(owner_user)
    if shop_id is not None and shop_id not in owned_ids:
        raise ValueError('Shop not found for this owner.')

    shops = (
        TailorProfile.objects.filter(owner=owner_user)
        .exclude(shop_name__isnull=True)
        .exclude(shop_name='')
        .order_by('-is_pinned', '-created_at')
    )
    if shop_id is not None:
        shops = shops.filter(id=shop_id)

    per_shop = []
    total_revenue = Decimal('0.00')
    total_orders = 0
    completed_orders = 0
    active_orders = 0

    for shop in shops:
        shop_orders = get_owner_orders_queryset(owner_user, shop_id=shop.id)
        delivered = shop_orders.filter(status__in=['delivered', 'collected'])
        shop_total_orders = shop_orders.count()
        shop_completed = delivered.count()
        shop_active = shop_orders.exclude(
            status__in=['delivered', 'collected', 'cancelled']
        ).count()
        shop_revenue = delivered.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

        per_shop.append({
            'shop_id': shop.id,
            'shop_name': shop.shop_name or '',
            'is_pinned': bool(shop.is_pinned),
            'orders': {
                'total': shop_total_orders,
                'completed': shop_completed,
                'active': shop_active,
            },
            'revenue': {
                'total_collected': _money(shop_revenue),
            },
            'shop_sales': get_shop_sales_summary(
                owner_user,
                period=sales_period,
                shop_id=shop.id,
            ),
        })

        total_revenue += shop_revenue
        total_orders += shop_total_orders
        completed_orders += shop_completed
        active_orders += shop_active

    aggregate_orders = get_owner_orders_queryset(owner_user, shop_id=shop_id)
    status_breakdown = {
        row['status']: row['count']
        for row in aggregate_orders.values('status').annotate(count=Count('id'))
    }

    return {
        'generated_at': timezone.now().isoformat(),
        'filters': {
            'shop_id': shop_id,
            'sales_period': sales_period,
        },
        'summary': {
            'shops_count': len(per_shop),
            'orders_total': total_orders,
            'orders_completed': completed_orders,
            'orders_active': active_orders,
            'revenue_total': _money(total_revenue),
            'status_breakdown': status_breakdown,
        },
        'shops': per_shop,
    }
