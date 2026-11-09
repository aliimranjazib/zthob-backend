"""
Daily tailor sales report via WSLA template mgask_daily_sales_report (9 body vars).

Template body (ar):
  {{1}} date, {{2}} shop name,
  {{3}}/{{4}} home delivery count/revenue,
  {{5}}/{{6}} walk-in count/revenue,
  {{7}}/{{8}} shop totals,
  {{9}} optional platform summary line.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone as dt_timezone
from decimal import Decimal
from typing import Callable
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db.models import Q, Sum
from django.utils import timezone

from apps.core.wsla_whatsapp_service import WslaWhatsAppService
from apps.orders.models import DailySalesWhatsAppDelivery, Order, OrderStatusHistory
from apps.tailors.models import TailorProfile

logger = logging.getLogger(__name__)

COMPLETED_STATUSES = ('delivered', 'collected')


def _money(value: Decimal | None) -> str:
    amount = value if isinstance(value, Decimal) else Decimal(str(value or '0'))
    return f'{amount.quantize(Decimal("0.01"))}'


def wsla_daily_sales_enabled() -> bool:
    return bool(getattr(settings, 'WSLA_WHATSAPP_ENABLED', False)) and bool(
        getattr(settings, 'WSLA_DAILY_SALES_REPORT_ENABLED', False)
    )


def _report_timezone() -> ZoneInfo:
    name = (getattr(settings, 'WSLA_DAILY_SALES_REPORT_TZ', 'Asia/Riyadh') or 'Asia/Riyadh').strip()
    try:
        return ZoneInfo(name)
    except Exception:
        return ZoneInfo('Asia/Riyadh')


def report_date_for_job(now: datetime | None = None) -> date:
    """Calendar day to report when the job runs (default: yesterday in report TZ)."""
    tz = _report_timezone()
    now = now or timezone.now()
    now_local = now.astimezone(tz)
    return now_local.date() - timedelta(days=1)


def utc_bounds_for_local_date(report_date: date) -> tuple[datetime, datetime]:
    tz = _report_timezone()
    start_local = datetime.combine(report_date, time.min, tzinfo=tz)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(dt_timezone.utc), end_local.astimezone(dt_timezone.utc)


@dataclass(frozen=True)
class SalesSlice:
    completed_count: int
    revenue: Decimal


def _order_ids_completed_in_window(
    *,
    start_utc: datetime,
    end_utc: datetime,
    shop_id: int | None = None,
) -> list[int]:
    q = OrderStatusHistory.objects.filter(
        created_at__gte=start_utc,
        created_at__lt=end_utc,
        status__in=COMPLETED_STATUSES,
    )
    if shop_id is not None:
        q = q.filter(order__shop_id=shop_id)
    return list(q.values_list('order_id', flat=True).distinct())


def aggregate_sales_for_orders(order_ids: list[int]) -> tuple[SalesSlice, SalesSlice, SalesSlice]:
    if not order_ids:
        empty = SalesSlice(0, Decimal('0'))
        return empty, empty, empty

    base = Order.objects.filter(id__in=order_ids)
    home_qs = base.filter(service_mode='home_delivery')
    walk_qs = base.filter(service_mode='walk_in')

    def _slice(qs) -> SalesSlice:
        paid_sum = qs.filter(payment_status='paid').aggregate(s=Sum('total_amount'))['s']
        return SalesSlice(qs.count(), paid_sum or Decimal('0'))

    home = _slice(home_qs)
    walk = _slice(walk_qs)
    total = SalesSlice(
        base.count(),
        base.filter(payment_status='paid').aggregate(s=Sum('total_amount'))['s'] or Decimal('0'),
    )
    return home, walk, total


def _platform_summary_line(
    home: SalesSlice,
    walk: SalesSlice,
    total: SalesSlice,
) -> str:
    if not getattr(settings, 'WSLA_DAILY_SALES_INCLUDE_PLATFORM_IN_LINE9', True):
        return 'تقرير يومي من مقاسك'
    return (
        f'المنصة: منزل {home.completed_count} طلب {_money(home.revenue)} ر.س | '
        f'محل {walk.completed_count} طلب {_money(walk.revenue)} ر.س | '
        f'الإجمالي {total.completed_count} طلب {_money(total.revenue)} ر.س'
    )[:900]


def build_daily_sales_parameters(
    *,
    report_date: date,
    shop_name: str,
    home: SalesSlice,
    walk: SalesSlice,
    total: SalesSlice,
    platform_home: SalesSlice,
    platform_walk: SalesSlice,
    platform_total: SalesSlice,
) -> list[str]:
    """Nine positional parameters for mgask_daily_sales_report."""
    return [
        report_date.isoformat(),
        (shop_name or 'Shop')[:200],
        str(home.completed_count),
        _money(home.revenue),
        str(walk.completed_count),
        _money(walk.revenue),
        str(total.completed_count),
        _money(total.revenue),
        _platform_summary_line(platform_home, platform_walk, platform_total),
    ]


def tailor_phone_for_shop(shop: TailorProfile) -> str | None:
    raw = (shop.contact_number or '').strip()
    if raw:
        return raw
    owner = getattr(shop, 'owner', None)
    if owner and getattr(owner, 'phone', None):
        return str(owner.phone).strip()
    user = getattr(shop, 'user', None)
    if user and getattr(user, 'phone', None):
        return str(user.phone).strip()
    return None


def _shop_eligible(shop: TailorProfile) -> bool:
    if not shop.shop_status:
        return False
    if getattr(settings, 'WSLA_DAILY_SALES_REQUIRE_TAILOR_PLUS', False):
        from apps.tailors.services.shop_plus import is_shop_plus_active

        if not is_shop_plus_active(shop.id):
            return False
    return tailor_phone_for_shop(shop) is not None


def send_daily_sales_report_for_shop(
    shop: TailorProfile,
    *,
    report_date: date,
    start_utc: datetime,
    end_utc: datetime,
    platform_home: SalesSlice,
    platform_walk: SalesSlice,
    platform_total: SalesSlice,
    send_fn: Callable[..., tuple[bool, str, str | None]] | None = None,
) -> bool:
    if not wsla_daily_sales_enabled():
        return False

    report_key = f'shop:{shop.id}:{report_date.isoformat()}'
    existing = DailySalesWhatsAppDelivery.objects.filter(
        report_key=report_key,
        status=DailySalesWhatsAppDelivery.STATUS_SENT,
    ).first()
    if existing:
        logger.info('Daily sales WhatsApp already sent %s', report_key)
        return True

    phone = tailor_phone_for_shop(shop)
    if not phone:
        return False

    order_ids = _order_ids_completed_in_window(
        start_utc=start_utc, end_utc=end_utc, shop_id=shop.id
    )
    home, walk, total = aggregate_sales_for_orders(order_ids)
    shop_name = (shop.shop_name or '').strip() or 'Shop'
    parameters = build_daily_sales_parameters(
        report_date=report_date,
        shop_name=shop_name,
        home=home,
        walk=walk,
        total=total,
        platform_home=platform_home,
        platform_walk=platform_walk,
        platform_total=platform_total,
    )
    template = getattr(
        settings, 'WSLA_TEMPLATE_DAILY_SALES_REPORT', 'mgask_daily_sales_report'
    ).strip()
    language = getattr(settings, 'WSLA_TEMPLATE_LANG', 'ar')

    send_fn = send_fn or WslaWhatsAppService.send_template
    success, detail, message_id = send_fn(
        phone_number=phone,
        template_name=template,
        language=language,
        body_parameters=parameters,
    )

    delivery, _ = DailySalesWhatsAppDelivery.objects.get_or_create(
        report_key=report_key,
        defaults={
            'shop': shop,
            'report_date': report_date,
            'status': DailySalesWhatsAppDelivery.STATUS_PENDING,
        },
    )
    delivery.shop = shop
    delivery.report_date = report_date
    delivery.phone_used = WslaWhatsAppService.format_number_for_wsla(phone)
    delivery.template_name = template
    delivery.attempt_count += 1
    delivery.last_attempt_at = timezone.now()

    if success:
        delivery.status = DailySalesWhatsAppDelivery.STATUS_SENT
        delivery.provider_message_id = message_id or ''
        delivery.error_message = ''
    else:
        delivery.status = DailySalesWhatsAppDelivery.STATUS_FAILED
        delivery.error_message = detail or 'Unknown error'
    delivery.save()

    if not success:
        logger.error('Daily sales WhatsApp failed shop=%s: %s', shop.id, detail)
    return bool(success)


def run_daily_sales_whatsapp_job(
    *,
    report_date: date | None = None,
    now: datetime | None = None,
) -> dict[str, int]:
    """
    Send mgask_daily_sales_report to each eligible shop.

    Returns counts: attempted, sent, skipped, failed.
    """
    stats = {'attempted': 0, 'sent': 0, 'skipped': 0, 'failed': 0}
    if not wsla_daily_sales_enabled():
        logger.info('Daily sales WhatsApp job skipped (disabled)')
        return stats

    report_date = report_date or report_date_for_job(now=now)
    start_utc, end_utc = utc_bounds_for_local_date(report_date)
    logger.info(
        'Daily sales WhatsApp: report_date=%s window_utc=[%s, %s)',
        report_date,
        start_utc,
        end_utc,
    )

    platform_ids = _order_ids_completed_in_window(
        start_utc=start_utc, end_utc=end_utc, shop_id=None
    )
    ph, pw, pt = aggregate_sales_for_orders(platform_ids)

    shops = TailorProfile.objects.select_related('owner', 'user').iterator()
    for shop in shops:
        if not _shop_eligible(shop):
            stats['skipped'] += 1
            continue
        stats['attempted'] += 1
        try:
            ok = send_daily_sales_report_for_shop(
                shop,
                report_date=report_date,
                start_utc=start_utc,
                end_utc=end_utc,
                platform_home=ph,
                platform_walk=pw,
                platform_total=pt,
            )
            if ok:
                stats['sent'] += 1
            else:
                stats['failed'] += 1
        except Exception:
            stats['failed'] += 1
            logger.exception('Daily sales WhatsApp error shop=%s', shop.id)
    return stats
