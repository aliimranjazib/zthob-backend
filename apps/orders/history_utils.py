from datetime import datetime, timedelta

from django.db.models import OuterRef, Subquery
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.orders.models import Order, OrderStatusHistory

COMPLETED_STATUSES = ('delivered', 'collected')

ALLOWED_PERIODS = (
    'today',
    'yesterday',
    'this_week',
    'this_month',
    'past_6_months',
    'custom',
)

DEFAULT_PERIOD = 'past_6_months'


def _parse_date(value, field_name):
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except (TypeError, ValueError) as exc:
        raise ValidationError({field_name: 'Must be a valid date in YYYY-MM-DD format.'}) from exc


def _make_aware_start(day):
    return timezone.make_aware(datetime.combine(day, datetime.min.time()))


def resolve_period_bounds(period, from_date=None, to_date=None):
    """
    Return (start, end) datetimes for a history period filter.
    End is exclusive (half-open interval [start, end)).
    """
    if period not in ALLOWED_PERIODS:
        raise ValidationError(
            {'period': f'Must be one of: {", ".join(ALLOWED_PERIODS)}.'}
        )

    now = timezone.now()
    today = timezone.localdate()
    today_start = _make_aware_start(today)
    tomorrow_start = today_start + timedelta(days=1)

    if period == 'today':
        return today_start, tomorrow_start

    if period == 'yesterday':
        yesterday = today - timedelta(days=1)
        return _make_aware_start(yesterday), today_start

    if period == 'this_week':
        week_start = today - timedelta(days=today.weekday())
        return _make_aware_start(week_start), tomorrow_start

    if period == 'this_month':
        month_start = today.replace(day=1)
        return _make_aware_start(month_start), tomorrow_start

    if period == 'past_6_months':
        six_months_ago = today - timedelta(days=180)
        return _make_aware_start(six_months_ago), tomorrow_start

    if period == 'custom':
        if not from_date or not to_date:
            raise ValidationError(
                {'period': 'Custom period requires both from_date and to_date (YYYY-MM-DD).'}
            )
        start_day = _parse_date(from_date, 'from_date')
        end_day = _parse_date(to_date, 'to_date')
        if start_day > end_day:
            raise ValidationError({'to_date': 'Must be on or after from_date.'})
        return _make_aware_start(start_day), _make_aware_start(end_day + timedelta(days=1))

    raise ValidationError({'period': 'Invalid period.'})


def annotate_completed_at(queryset):
    completion_history = OrderStatusHistory.objects.filter(
        order=OuterRef('pk'),
        status__in=COMPLETED_STATUSES,
    ).order_by('-created_at')

    return queryset.annotate(
        completed_at=Coalesce(
            Subquery(completion_history.values('created_at')[:1]),
            'updated_at',
        )
    )


def get_tailor_completed_orders(tailor_user, period=DEFAULT_PERIOD, from_date=None, to_date=None):
    start, end = resolve_period_bounds(period, from_date=from_date, to_date=to_date)

    queryset = Order.objects.filter(
        tailor=tailor_user,
        status__in=COMPLETED_STATUSES,
    )
    queryset = annotate_completed_at(queryset)
    queryset = queryset.filter(
        completed_at__gte=start,
        completed_at__lt=end,
    ).select_related(
        'customer',
        'delivery_address',
        'rider__rider_profile',
        'assigned_rider__rider_profile',
        'measurement_rider__rider_profile',
        'delivery_rider__rider_profile',
    ).prefetch_related('order_items__fabric').order_by('-completed_at')

    return queryset, start, end
