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
        missing = []
        if not settings.TWILIO_ACCOUNT_SID:
            missing.append("TWILIO_ACCOUNT_SID")
        if not settings.TWILIO_AUTH_TOKEN:
            missing.append("TWILIO_AUTH_TOKEN")
        if not settings.TWILIO_PHONE_NUMBER:
            missing.append("TWILIO_PHONE_NUMBER")
        
        if missing:
            error_msg = f"Twilio not configured. Missing: {', '.join(missing)}"
            logger.error(error_msg)
            return False, error_msg
        
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
            error_msg = str(e)
            logger.error(f"Twilio error: {error_msg}")
            
            # Provide more specific error messages
            if "401" in error_msg or "Authenticate" in error_msg:
                return False, f"Failed to send SMS: HTTP 401 error: Unable to create record: Authenticate. Please check TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN are correct."
            elif "403" in error_msg:
                return False, f"Failed to send SMS: HTTP 403 error: Forbidden. Please check Twilio account permissions."
            else:
                return False, f"Failed to send SMS: {error_msg}"
        except Exception as e:
            logger.error(f"Unexpected error sending SMS: {str(e)}")
            return False, f"Failed to send SMS: {str(e)}"
    
    @staticmethod
    def format_phone_number(phone_number: str) -> str:
        """
        Format phone number to E.164 format
        
        Handles Saudi Arabia and Pakistan numbers:
        Saudi:
        - 0501234567 → +966501234567
        - 501234567 → +966501234567
        - 966501234567 → +966501234567
        
        Pakistan:
        - 03076900096 → +923076900096
        - 3076900096 → +923076900096
        - 923076900096 → +923076900096
        
        Args:
            phone_number: Phone number in various formats
            
        Returns:
            str: Formatted phone number in E.164 format
        """
        # Remove all non-digit characters
        digits = ''.join(filter(str.isdigit, phone_number))
        
        # If already in E.164 format, return as is
        if phone_number.startswith('+'):
            return phone_number
        
        # Handle Saudi Arabia numbers
        if digits.startswith('05') and len(digits) == 10:
            # Saudi mobile: 05xxxxxxxx -> +9665xxxxxxxx
            return '+966' + digits[1:]
        elif digits.startswith('5') and len(digits) == 9:
            # Saudi mobile without leading 0: 5xxxxxxxx -> +9665xxxxxxxx
            return '+966' + digits
        elif digits.startswith('966') and len(digits) >= 12:
            # Already has Saudi country code: 9665xxxxxxxx -> +9665xxxxxxxx
            return '+' + digits
        # Handle Pakistan numbers
        elif digits.startswith('03') and len(digits) == 11:
            # Pakistan mobile: 03xxxxxxxxx -> +923xxxxxxxxx
            return '+92' + digits[1:]
        elif digits.startswith('3') and len(digits) == 10:
            # Pakistan mobile without leading 0: 3xxxxxxxxx -> +923xxxxxxxxx
            return '+92' + digits
        elif digits.startswith('923') and len(digits) >= 12:
            # Already has Pakistan country code: 923xxxxxxxxx -> +923xxxxxxxxx
            return '+' + digits
        else:
            # Default: try to detect based on length and prefix
            if len(digits) == 10 and digits.startswith('05'):
                # Saudi format
                return '+966' + digits[1:]
            elif len(digits) == 11 and digits.startswith('03'):
                # Pakistan format
                return '+92' + digits[1:]
            # Fallback: assume it's already in correct format or add +
            return '+' + digits if not phone_number.startswith('+') else phone_number
    
    @staticmethod
    def send_verification_code(phone_number: str, locale: str = 'en') -> tuple[bool, str, str]:
        """
        Send verification code using Twilio Verify API
        
        Args:
            phone_number: Phone number in E.164 format (e.g., +966501234567)
            locale: Language locale (e.g., 'en', 'ar')
            
        Returns:
            tuple: (success: bool, message: str, verification_sid: str)
        """
        # Check if Twilio SDK is available
        if not TWILIO_AVAILABLE:
            logger.error("Twilio SDK not installed. Please install twilio package.")
            return False, "SMS service not available - Twilio SDK not installed", ""
        
        # Check if Twilio Verify is configured
        if not settings.TWILIO_ACCOUNT_SID:
            return False, "Twilio not configured. Missing TWILIO_ACCOUNT_SID", ""
        if not settings.TWILIO_AUTH_TOKEN:
            return False, "Twilio not configured. Missing TWILIO_AUTH_TOKEN", ""
        if not settings.TWILIO_VERIFY_SERVICE_SID:
            return False, "Twilio Verify not configured. Missing TWILIO_VERIFY_SERVICE_SID", ""
        
        try:
            # Initialize Twilio client
            client = Client(
                settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN
            )
            
            # Format phone number (ensure it starts with +)
            formatted_phone = TwilioSMSService.format_phone_number(phone_number)
            
            # Send verification code using Twilio Verify API
            verification = client.verify.v2.services(
                settings.TWILIO_VERIFY_SERVICE_SID
            ).verifications.create(
                to=formatted_phone,
                channel='sms',
                locale=locale
            )
            
            logger.info(f"Twilio Verify code sent. SID: {verification.sid}, To: {formatted_phone}")
            return True, f"Verification code sent successfully", verification.sid
            
        except TwilioRestException as e:
            error_msg = str(e)
            logger.error(f"Twilio Verify error: {error_msg}")
            
            # Provide more specific error messages
            if "401" in error_msg or "Authenticate" in error_msg:
                return False, f"Failed to send verification code: HTTP 401 error. Please check TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN are correct.", ""
            elif "403" in error_msg:
                return False, f"Failed to send verification code: HTTP 403 error. Please check Twilio account permissions.", ""
            else:
                return False, f"Failed to send verification code: {error_msg}", ""
        except Exception as e:
            logger.error(f"Unexpected error sending verification code: {str(e)}")
            return False, f"Failed to send verification code: {str(e)}", ""
    
    @staticmethod
    def verify_code(phone_number: str, code: str) -> tuple[bool, str]:
        """
        Verify code using Twilio Verify API
        
        Args:
            phone_number: Phone number in E.164 format (e.g., +966501234567)
            code: Verification code to check
            
        Returns:
            tuple: (is_valid: bool, message: str)
        """
        # Check if Twilio SDK is available
        if not TWILIO_AVAILABLE:
            logger.error("Twilio SDK not installed.")
            return False, "SMS service not available - Twilio SDK not installed"
        
        # Check if Twilio Verify is configured
        if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
            return False, "Twilio not configured"
        if not settings.TWILIO_VERIFY_SERVICE_SID:
            return False, "Twilio Verify not configured. Missing TWILIO_VERIFY_SERVICE_SID"
        
        try:
            # Initialize Twilio client
            client = Client(
                settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN
            )
            
            # Format phone number
            formatted_phone = TwilioSMSService.format_phone_number(phone_number)
            
            # Verify the code using Twilio Verify API
            verification_check = client.verify.v2.services(
                settings.TWILIO_VERIFY_SERVICE_SID
            ).verification_checks.create(
                to=formatted_phone,
                code=code
            )
            
            if verification_check.status == 'approved':
                logger.info(f"Twilio Verify code verified successfully. To: {formatted_phone}")
                return True, "Phone verified successfully!"
            else:
                logger.warning(f"Twilio Verify code verification failed. Status: {verification_check.status}, To: {formatted_phone}")
                return False, "Invalid or expired verification code"
                
        except TwilioRestException as e:
            error_msg = str(e)
            logger.error(f"Twilio Verify error: {error_msg}")
            
            if "404" in error_msg or "not found" in error_msg.lower():
                return False, "Verification code not found or expired"
            else:
                return False, f"Failed to verify code: {error_msg}"
        except Exception as e:
            logger.error(f"Unexpected error verifying code: {str(e)}")
            return False, f"Failed to verify code: {str(e)}"

