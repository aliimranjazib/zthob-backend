import logging

from celery import shared_task

from apps.customers.services.welcome_sms import send_customer_welcome_sms

logger = logging.getLogger(__name__)


@shared_task(name='apps.customers.tasks.send_customer_welcome_sms_task')
def send_customer_welcome_sms_task(user_id):
    """Background task to send customer onboarding welcome SMS."""
    try:
        return send_customer_welcome_sms(user_id)
    except Exception as exc:
        logger.exception('Error sending welcome SMS to user %s: %s', user_id, exc)
        return False
