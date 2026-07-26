from celery import shared_task
from .taqnyat_service import TaqnyatSMSService, TaqnyatVerifyService
from .phone_format import format_phone_e164
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
    except Exception as e:
        logger.error(f"Error in send_otp_sms_task: {str(e)}")
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
    except Exception as e:
        logger.error(f"Error in send_verification_code_task: {str(e)}")
        return False
