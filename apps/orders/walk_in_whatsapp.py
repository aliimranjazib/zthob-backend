"""Walk-in customer WhatsApp notifications via WSLA."""

from __future__ import annotations

import logging
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.core.customer_deep_link import walk_in_whatsapp_url_button_suffix
from apps.core.phone_format import normalize_phone_to_local
from apps.core.phone_utils import display_user_label
from apps.core.wsla_whatsapp_service import WslaWhatsAppService
from apps.notifications.services import NotificationService
from apps.orders.models import Order, WalkInWhatsAppDelivery

logger = logging.getLogger(__name__)

EVENT_ORDER_CREATED = 'order_created'
EVENT_READY_FOR_PICKUP = 'ready_for_pickup'

WALK_IN_WHATSAPP_ORDER_TYPES = frozenset(
    {'fabric_with_stitching', 'stitching_only', 'fabric_only', 'measurement_service'}
)


def wsla_whatsapp_enabled() -> bool:
    return bool(getattr(settings, 'WSLA_WHATSAPP_ENABLED', False))


def walk_in_order_url_button_enabled() -> bool:
    if not getattr(settings, 'WSLA_WALK_IN_ORDER_URL_BUTTON_ENABLED', True):
        return False
    base = (getattr(settings, 'CUSTOMER_ORDER_DEEP_LINK_BASE', '') or '').strip()
    return bool(base)


def _shop_profile(order: Order):
    return getattr(order, 'shop', None)


def _shop_phone(order: Order) -> str:
    shop = _shop_profile(order)
    if shop and (shop.contact_number or '').strip():
        return normalize_phone_to_local(shop.contact_number.strip())
    owner = getattr(shop, 'owner', None) if shop else None
    if owner and getattr(owner, 'phone', None):
        return normalize_phone_to_local(owner.phone)
    tailor = order.tailor
    if tailor and getattr(tailor, 'phone', None):
        return normalize_phone_to_local(tailor.phone)
    return '-'


def _shop_address(order: Order) -> str:
    shop = _shop_profile(order)
    if not shop:
        return '-'
    address = (shop.address or '').strip()
    if not address:
        return '-'
    max_len = int(getattr(settings, 'WSLA_WHATSAPP_ADDRESS_MAX_LEN', 200))
    if len(address) > max_len:
        return address[: max_len - 3] + '...'
    return address


def _shop_name(order: Order) -> str:
    shop = _shop_profile(order)
    if shop and shop.shop_name:
        return shop.shop_name.strip()
    return 'Shop'


def _money(value) -> str:
    amount = value if isinstance(value, Decimal) else Decimal(str(value or '0'))
    return f'{amount.quantize(Decimal("0.01"))}'


def _expected_delivery(order: Order) -> str:
    if order.stitching_completion_date:
        return order.stitching_completion_date.isoformat()
    return '-'


def _customer_phone(order: Order) -> str | None:
    customer = order.customer
    if not customer or not (customer.phone or '').strip():
        return None
    return customer.phone.strip()


def should_send_walk_in_whatsapp(order: Order, event: str) -> bool:
    if not wsla_whatsapp_enabled():
        return False
    if order.service_mode != 'walk_in':
        return False
    if order.order_type not in WALK_IN_WHATSAPP_ORDER_TYPES:
        return False
    if event == EVENT_ORDER_CREATED:
        if order.payment_status != 'paid':
            return False
    elif event == EVENT_READY_FOR_PICKUP:
        if order.status != 'ready_for_pickup':
            return False
    else:
        return False

    if getattr(settings, 'WSLA_WALK_IN_REQUIRE_TAILOR_PLUS', False):
        from apps.tailors.services.shop_plus import is_shop_plus_active

        if not is_shop_plus_active(order.shop_id):
            return False

    return _customer_phone(order) is not None


def build_order_created_parameters(order: Order) -> list[str]:
    """Approved template mgask_walk_in_order_created: {{1}}..{{7}} positional."""
    return [
        display_user_label(order.customer),
        _shop_name(order),
        order.order_number or str(order.id),
        _money(order.total_amount),
        _expected_delivery(order),
        _shop_phone(order),
        _shop_address(order),
    ]


def build_ready_for_pickup_parameters(order: Order) -> list[str]:
    """Approved template mgask_walk_in_ready: {{1}}..{{5}} positional."""
    return [
        display_user_label(order.customer),
        order.order_number or str(order.id),
        _shop_name(order),
        _shop_address(order),
        _shop_phone(order),
    ]


def _template_name_for_event(event: str) -> str:
    if event == EVENT_ORDER_CREATED:
        return getattr(settings, 'WSLA_TEMPLATE_WALK_IN_CREATED', 'mgask_walk_in_order_created')
    if event == EVENT_READY_FOR_PICKUP:
        return getattr(settings, 'WSLA_TEMPLATE_WALK_IN_READY', 'mgask_walk_in_ready')
    raise ValueError(f'Unknown walk-in WhatsApp event: {event}')


def _notify_customer_push(order: Order, event: str) -> None:
    if not order.customer:
        return
    order_number = order.order_number
    if event == EVENT_ORDER_CREATED:
        title = 'Order #{order_number} created'
        body = (
            'Your order has been created. Order #{order_number} — '
            'we sent the details to your WhatsApp when your phone is on file.'
        )
        category = 'walk_in_order_created'
    else:
        title = 'Order #{order_number} ready for pickup'
        body = 'Your order #{order_number} is ready to pick up at the shop.'
        category = 'walk_in_ready_for_pickup'

    NotificationService.send_notification(
        user=order.customer,
        title=title,
        body=body,
        notification_type='ORDER_STATUS',
        category=category,
        data={
            'order_id': order.id,
            'order_number': order_number,
            'service_mode': order.service_mode,
            'status': order.status,
        },
        priority='high',
        app_role='CUSTOMER',
        language_override='ar',
    )


def send_walk_in_whatsapp(order_id: int, event: str) -> bool:
    try:
        order = Order.objects.select_related('customer', 'shop', 'shop__owner', 'tailor').get(pk=order_id)
    except Order.DoesNotExist:
        logger.error('Walk-in WhatsApp: order %s not found', order_id)
        return False

    if not should_send_walk_in_whatsapp(order, event):
        logger.info('Skipping walk-in WhatsApp %s for order %s', event, order_id)
        return False

    phone = _customer_phone(order)
    if not phone:
        return False

    delivery, created = WalkInWhatsAppDelivery.objects.get_or_create(
        order=order,
        event=event,
        defaults={'status': WalkInWhatsAppDelivery.STATUS_PENDING},
    )
    if not created and delivery.status == WalkInWhatsAppDelivery.STATUS_SENT:
        logger.info('Walk-in WhatsApp already sent for order %s event %s', order_id, event)
        return True

    if event == EVENT_ORDER_CREATED:
        parameters = build_order_created_parameters(order)
    else:
        parameters = build_ready_for_pickup_parameters(order)

    template_name = _template_name_for_event(event)
    language = getattr(settings, 'WSLA_TEMPLATE_LANG', 'ar')

    url_suffix = None
    if walk_in_order_url_button_enabled():
        url_suffix = walk_in_whatsapp_url_button_suffix(order.id)

    success, detail, message_id = WslaWhatsAppService.send_template(
        phone_number=phone,
        template_name=template_name,
        language=language,
        body_parameters=parameters,
        url_button_suffix=url_suffix,
    )

    delivery.phone_used = WslaWhatsAppService.format_number_for_wsla(phone)
    delivery.template_name = template_name
    delivery.attempt_count += 1
    delivery.last_attempt_at = timezone.now()

    if success:
        delivery.status = WalkInWhatsAppDelivery.STATUS_SENT
        delivery.provider_message_id = message_id or ''
        delivery.error_message = ''
        delivery.save()
        try:
            _notify_customer_push(order, event)
        except Exception:
            logger.exception('Walk-in push notification failed for order %s', order_id)
        return True

    delivery.status = WalkInWhatsAppDelivery.STATUS_FAILED
    delivery.error_message = detail or 'Unknown error'
    delivery.save()
    logger.error('Walk-in WhatsApp failed for order %s (%s): %s', order_id, event, detail)
    return False


def schedule_walk_in_whatsapp(order_id: int, event: str) -> None:
    if not wsla_whatsapp_enabled():
        return

    def _dispatch():
        from apps.orders.tasks import send_walk_in_whatsapp_task

        if getattr(settings, 'WSLA_WHATSAPP_SYNC', False):
            send_walk_in_whatsapp(order_id, event)
            return
        try:
            send_walk_in_whatsapp_task.delay(order_id, event)
        except Exception:
            logger.exception(
                'Celery unavailable; sending walk-in WhatsApp synchronously for order %s',
                order_id,
            )
            send_walk_in_whatsapp(order_id, event)

    transaction.on_commit(_dispatch)


def maybe_schedule_ready_for_pickup_whatsapp(order: Order, *, old_status: str) -> None:
    if order.service_mode != 'walk_in':
        return
    if order.status != 'ready_for_pickup':
        return
    if old_status == 'ready_for_pickup':
        return
    schedule_walk_in_whatsapp(order.id, EVENT_READY_FOR_PICKUP)


def walk_in_order_created_api_message(order: Order) -> str:
    if order.service_mode != 'walk_in':
        return 'Order created successfully'
    if wsla_whatsapp_enabled() and _customer_phone(order):
        return (
            'Order created successfully. Customer will receive order details on WhatsApp.'
        )
    if wsla_whatsapp_enabled():
        return (
            'Order created successfully. WhatsApp was not sent — customer has no phone on file.'
        )
    return 'Order created successfully'
