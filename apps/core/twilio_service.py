import logging
from django.conf import settings

logger = logging.getLogger(__name__)

# Try to import Twilio (optional - only if using Twilio)
try:
    from twilio.rest import Client
    from twilio.base.exceptions import TwilioRestException
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    logger.info("Twilio SDK not available - SMS functionality will be disabled")

class TwilioSMSService:
    """Service for sending SMS via Twilio"""
    
    @staticmethod
    def send_otp_sms(phone_number: str, otp_code: str) -> tuple[bool, str]:
        """
        Send OTP via SMS using Twilio
        
        Args:
            phone_number: Phone number in E.164 format (e.g., +966501234567)
            otp_code: 6-digit OTP code
            
        Returns:
            tuple: (success: bool, message: str)
        """
        # Check if Twilio SDK is available
        if not TWILIO_AVAILABLE:
            logger.error("Twilio SDK not installed. Please install twilio package.")
            return False, "SMS service not available - Twilio SDK not installed"
        
        # Check if Twilio is configured
        if not all([
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN,
            settings.TWILIO_PHONE_NUMBER
        ]):
            logger.error("Twilio not configured. Missing credentials in settings.")
            return False, "SMS service not configured"
        
        try:
            # Initialize Twilio client
            client = Client(
                settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN
            )
            
            # Format phone number (ensure it starts with +)
            formatted_phone = TwilioSMSService.format_phone_number(phone_number)
            
            # Create SMS message
            message_body = f"Your Mgask verification code is: {otp_code}. Valid for 5 minutes."
            
            # Send SMS
            message = client.messages.create(
                body=message_body,
                from_=settings.TWILIO_PHONE_NUMBER,
                to=formatted_phone
            )
            
            logger.info(f"SMS sent successfully. SID: {message.sid}, To: {formatted_phone}")
            return True, f"SMS sent successfully. SID: {message.sid}"
            
        except TwilioRestException as e:
            logger.error(f"Twilio error: {str(e)}")
            return False, f"Failed to send SMS: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error sending SMS: {str(e)}")
            return False, f"Failed to send SMS: {str(e)}"
    
    @staticmethod
    def format_phone_number(phone_number: str) -> str:
        """
        Format phone number to E.164 format
        
        Handles Saudi numbers:
        - 0501234567 → +966501234567
        - 501234567 → +966501234567
        - 966501234567 → +966501234567
        
        Args:
            phone_number: Phone number in various formats
            
        Returns:
            str: Formatted phone number in E.164 format
        """
        # Remove all non-digit characters
        digits = ''.join(filter(str.isdigit, phone_number))
        
        # Handle Saudi numbers
        if digits.startswith('05') and len(digits) == 10:
            # Saudi mobile: 05xxxxxxxx -> +9665xxxxxxxx
            return '+966' + digits[1:]
        elif digits.startswith('5') and len(digits) == 9:
            # Saudi mobile without leading 0: 5xxxxxxxx -> +9665xxxxxxxx
            return '+966' + digits
        elif digits.startswith('966') and len(digits) >= 12:
            # Already has country code: 9665xxxxxxxx -> +9665xxxxxxxx
            return '+' + digits
        elif phone_number.startswith('+'):
            # Already in E.164 format
            return phone_number
        else:
            # Default: assume Saudi number
            if len(digits) == 10 and digits.startswith('05'):
                return '+966' + digits[1:]
            return '+' + digits

