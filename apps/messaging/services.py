import logging

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.core.phone_format import format_phone_e164
from apps.core.taqnyat_service import TaqnyatSMSService
from apps.notifications.services import NotificationService

from .models import AdminMessageDelivery, AdminOutboundMessage

logger = logging.getLogger(__name__)
User = get_user_model()


def _user_app_role(user) -> str:
  role = getattr(user, 'role', 'USER')
  if role == 'TAILOR':
    return 'TAILOR'
  if role == 'RIDER':
    return 'RIDER'
  return 'CUSTOMER'


def _active_users_queryset():
  return User.objects.filter(is_active=True, is_deleted=False)


def resolve_recipients(message: AdminOutboundMessage):
  """Return the list of users who should receive this message."""
  if message.audience_type == 'single':
    if message.target_user_id and message.target_user.is_active and not message.target_user.is_deleted:
      return [message.target_user]
    return []

  if message.audience_type == 'role':
    if not message.target_role:
      return []
    return list(_active_users_queryset().filter(role=message.target_role))

  if message.audience_type == 'selected':
    return list(message.recipients.filter(is_active=True, is_deleted=False))

  return []


def _send_sms_to_user(message: AdminOutboundMessage, user, delivery: AdminMessageDelivery) -> bool:
  phone = (user.phone or '').strip()
  if not phone:
    delivery.sms_status = 'skipped'
    delivery.error_message = (delivery.error_message + ' No phone number on file.').strip()
    return False

  try:
    formatted_phone = format_phone_e164(phone)
  except Exception as exc:
    delivery.sms_status = 'failed'
    delivery.error_message = (delivery.error_message + f' Invalid phone: {exc}').strip()
    return False

  delivery.phone_used = formatted_phone
  success, detail, message_id = TaqnyatSMSService.send_sms(formatted_phone, message.body)
  if success:
    delivery.sms_status = 'sent'
    if message_id:
      delivery.provider_message_id = message_id
    return True

  delivery.sms_status = 'failed'
  delivery.error_message = (delivery.error_message + f' SMS: {detail}').strip()
  return False


def _send_push_to_user(message: AdminOutboundMessage, user, delivery: AdminMessageDelivery) -> bool:
  title = (message.title or '').strip() or 'Mgask'
  success = NotificationService.send_notification(
    user=user,
    title=title,
    body=message.body,
    notification_type='SYSTEM',
    category='admin_message',
    data={'admin_message_id': message.id},
    app_role=_user_app_role(user),
  )
  if success:
    delivery.push_status = 'sent'
    return True

  delivery.push_status = 'failed'
  delivery.error_message = (delivery.error_message + ' Push: delivery failed.').strip()
  return False


def _finalize_delivery_status(delivery: AdminMessageDelivery, channel: str):
  sms_ok = delivery.sms_status in ('sent', 'skipped')
  push_ok = delivery.push_status in ('sent', 'skipped')

  if channel == 'sms':
    if delivery.sms_status == 'sent':
      delivery.status = 'sent'
    elif delivery.sms_status == 'skipped':
      delivery.status = 'skipped'
    else:
      delivery.status = 'failed'
  elif channel == 'push':
    if delivery.push_status == 'sent':
      delivery.status = 'sent'
    else:
      delivery.status = 'failed'
  else:
    if delivery.sms_status == 'sent' and delivery.push_status == 'sent':
      delivery.status = 'sent'
    elif delivery.sms_status == 'sent' or delivery.push_status == 'sent':
      delivery.status = 'partial'
    elif delivery.sms_status == 'skipped' and delivery.push_status == 'failed':
      delivery.status = 'failed'
    elif delivery.sms_status == 'failed' and delivery.push_status == 'skipped':
      delivery.status = 'failed'
    else:
      delivery.status = 'failed'


def process_admin_message(message_id: int):
  """Deliver an admin outbound message to all resolved recipients."""
  try:
    message = AdminOutboundMessage.objects.get(pk=message_id)
  except AdminOutboundMessage.DoesNotExist:
    logger.error('AdminOutboundMessage %s not found', message_id)
    return False

  if message.status in ('completed', 'processing'):
    return message.status == 'completed'

  message.status = 'processing'
  message.save(update_fields=['status', 'updated_at'])

  recipients = resolve_recipients(message)
  message.total_recipients = len(recipients)
  sent_count = 0
  failed_count = 0
  errors = []

  for user in recipients:
    delivery, _created = AdminMessageDelivery.objects.get_or_create(
      message=message,
      user=user,
      defaults={'created_by': message.sent_by},
    )

    channel = message.channel
    sms_result = push_result = True

    if channel in ('sms', 'both'):
      sms_result = _send_sms_to_user(message, user, delivery)
    else:
      delivery.sms_status = 'skipped'

    if channel in ('push', 'both'):
      push_result = _send_push_to_user(message, user, delivery)
    else:
      delivery.push_status = 'skipped'

    _finalize_delivery_status(delivery, channel)
    delivery.sent_at = timezone.now()
    delivery.save()

    if delivery.status in ('sent', 'partial'):
      sent_count += 1
    else:
      failed_count += 1
      if delivery.error_message:
        errors.append(f'{user.username}: {delivery.error_message}')

  message.sent_count = sent_count
  message.failed_count = failed_count
  message.sent_at = timezone.now()
  message.error_summary = '\n'.join(errors[:20])
  if not recipients:
    message.status = 'failed'
    message.error_summary = 'No recipients matched the selected audience.'
  elif failed_count == 0:
    message.status = 'completed'
  elif sent_count == 0:
    message.status = 'failed'
  else:
    message.status = 'completed'
  message.save(
    update_fields=[
      'status',
      'sent_at',
      'total_recipients',
      'sent_count',
      'failed_count',
      'error_summary',
      'updated_at',
    ]
  )
  return message.status == 'completed'
