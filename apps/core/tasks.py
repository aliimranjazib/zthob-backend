from celery import shared_task
from .taqnyat_service import TaqnyatSMSService, TaqnyatVerifyService
from .phone_format import format_phone_e164
from zthob.monitoring.sentry import capture_task_exception
import logging

logger = logging.getLogger(__name__)

@shared_task(name="apps.core.tasks.send_otp_sms_task")
def send_otp_sms_task(phone_number, otp_code):
    """Background task to send OTP via Taqnyat SMS."""
    try:
        formatted_phone = format_phone_e164(phone_number)
        success, message = TaqnyatSMSService.send_otp_sms(
            phone_number=formatted_phone,
            otp_code=otp_code,
        )
        if not success:
            logger.error(f"Failed to send SMS OTP to {formatted_phone}: {message}")
        return success
    except Exception as exc:
        logger.exception("Error in send_otp_sms_task for %s", phone_number)
        capture_task_exception(exc, task_name='send_otp_sms_task', phone_number=phone_number)
        return False


@shared_task(name="apps.core.tasks.send_sms_task")
def send_sms_task(phone_number, body):
    """Background task to send a plain SMS via Taqnyat."""
    try:
        formatted_phone = format_phone_e164(phone_number)
        success, message, _message_id = TaqnyatSMSService.send_sms(
            phone_number=formatted_phone,
            body=body,
        )
        if not success:
            logger.error(f"Failed to send SMS to {formatted_phone}: {message}")
        return success
    except Exception as exc:
        logger.exception("Error in send_sms_task for %s", phone_number)
        capture_task_exception(exc, task_name='send_sms_task', phone_number=phone_number)
        return False

@shared_task(name="apps.core.tasks.send_verification_code_task")
def send_verification_code_task(phone_number, locale='ar', verification_id=None):
    """Background task to send Taqnyat Verify OTP."""
    from .models import PhoneVerification
    try:
        verification = PhoneVerification.objects.get(id=verification_id)
        success, message = TaqnyatVerifyService.send_verification_code(
            phone_number=phone_number,
            request_id=verification.verification_sid,
            lang=locale,
        )
        if not success:
            logger.error(f"Failed to send Taqnyat Verify code to {phone_number}: {message}")
        return success
    except PhoneVerification.DoesNotExist:
        logger.error(f"PhoneVerification {verification_id} not found for Taqnyat send task")
        return False
    except Exception as exc:
        logger.exception("Error in send_verification_code_task for %s", phone_number)
        capture_task_exception(
            exc,
            task_name='send_verification_code_task',
            phone_number=phone_number,
            verification_id=verification_id,
        )
        return False
