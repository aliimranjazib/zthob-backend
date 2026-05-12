from celery import shared_task
from .twilio_service import TwilioSMSService
import logging

logger = logging.getLogger(__name__)

@shared_task(name="apps.core.tasks.send_otp_sms_task")
def send_otp_sms_task(phone_number, otp_code):
    """
    Background task to send OTP via SMS.
    """
    try:
        formatted_phone = TwilioSMSService.format_phone_number(phone_number)
        success, message = TwilioSMSService.send_otp_sms(
            phone_number=formatted_phone,
            otp_code=otp_code
        )
        if not success:
            logger.error(f"Failed to send SMS OTP to {formatted_phone}: {message}")
        return success
    except Exception as e:
        logger.error(f"Error in send_otp_sms_task: {str(e)}")
        return False

@shared_task(name="apps.core.tasks.send_verification_code_task")
def send_verification_code_task(phone_number, locale='en', verification_id=None):
    """
    Background task to send Twilio Verify code and update the record with SID.
    """
    from .models import PhoneVerification
    try:
        success, message, sid = TwilioSMSService.send_verification_code(
            phone_number=phone_number,
            locale=locale
        )
        if success and verification_id:
            PhoneVerification.objects.filter(id=verification_id).update(verification_sid=sid)
        elif not success:
            logger.error(f"Failed to send Twilio Verify code to {phone_number}: {message}")
        return success
    except Exception as e:
        logger.error(f"Error in send_verification_code_task: {str(e)}")
        return False
