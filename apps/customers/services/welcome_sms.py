import logging

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.core.phone_format import format_phone_e164
from apps.core.taqnyat_service import TaqnyatSMSService
from apps.customers.models import CustomerProfile

logger = logging.getLogger(__name__)
User = get_user_model()

CUSTOMER_WELCOME_SMS_BODY = """مرحبًا،

تم تسجيلكم بنجاح في تطبيق مقاسك لتفصيل الثياب باستخدام رقم الجوال الخاص بكم.

للدخول إلى حسابكم ومتابعة طلبكم، يرجى تحميل التطبيق من خلال الرابط التالي:
www.mgask.sa"""


def should_send_welcome_sms(profile: CustomerProfile | None) -> bool:
    if profile is None:
        return True
    return profile.welcome_sms_sent_at is None


def send_customer_welcome_sms(user_id: int) -> bool:
    """
    Send the onboarding welcome SMS to a customer if not already sent.

    Returns True when SMS was sent successfully.
    """
    try:
        user = User.objects.select_related('customer_profile').get(pk=user_id)
    except User.DoesNotExist:
        logger.error('Cannot send welcome SMS: user %s not found', user_id)
        return False

    phone = (user.phone or '').strip()
    if not phone:
        logger.warning('Skipping welcome SMS for user %s: no phone number', user_id)
        return False

    profile = getattr(user, 'customer_profile', None)
    if not should_send_welcome_sms(profile):
        logger.info('Skipping welcome SMS for user %s: already sent', user_id)
        return False

    try:
        formatted_phone = format_phone_e164(phone)
    except Exception as exc:
        logger.error('Skipping welcome SMS for user %s: invalid phone (%s)', user_id, exc)
        return False

    success, message, _message_id = TaqnyatSMSService.send_sms(
        formatted_phone,
        CUSTOMER_WELCOME_SMS_BODY,
    )
    if not success:
        logger.error('Failed to send welcome SMS to user %s: %s', user_id, message)
        return False

    if profile is None:
        profile, _created = CustomerProfile.objects.get_or_create(user=user)

    profile.welcome_sms_sent_at = timezone.now()
    profile.save(update_fields=['welcome_sms_sent_at'])
    logger.info('Welcome SMS sent to user %s', user_id)
    return True


def queue_customer_welcome_sms(user_id: int) -> None:
    """Queue welcome SMS delivery via Celery."""
    try:
        user = User.objects.select_related('customer_profile').get(pk=user_id)
    except User.DoesNotExist:
        logger.error('Cannot queue welcome SMS: user %s not found', user_id)
        return

    phone = (user.phone or '').strip()
    if not phone:
        return

    profile = getattr(user, 'customer_profile', None)
    if not should_send_welcome_sms(profile):
        return

    from apps.customers.tasks import send_customer_welcome_sms_task

    send_customer_welcome_sms_task.delay(user_id)
