import random
import logging
from django.utils import timezone
from datetime import timedelta
from .models import PhoneVerification
from .twilio_service import TwilioSMSService

logger = logging.getLogger(__name__)

class PhoneVerificationService:
    """Reusable service for phone verification"""
    
    @staticmethod
    def generate_otp():
        """Generate 6-digit OTP"""
        return str(random.randint(100000, 999999))
    
    @staticmethod
    def create_verification(user, phone_number):
        """Create new phone verification record and send OTP via SMS"""
        # Generate OTP
        otp_code = PhoneVerificationService.generate_otp()
        
        # Set expiration (5 minutes from now)
        expires_at = timezone.now() + timedelta(minutes=5)
        
        # Create verification record
        verification = PhoneVerification.objects.create(
            user=user,
            phone_number=phone_number,
            otp_code=otp_code,
            expires_at=expires_at
        )
        
        # Send OTP via SMS using Twilio
        formatted_phone = TwilioSMSService.format_phone_number(phone_number)
        sms_success, sms_message = TwilioSMSService.send_otp_sms(
            phone_number=formatted_phone,
            otp_code=otp_code
        )
        
        if not sms_success:
            # Log error but don't fail - OTP is still created
            logger.error(f"Failed to send SMS OTP to {formatted_phone}: {sms_message}")
            logger.error(f"OTP Code: {otp_code} (for manual testing if SMS fails)")
        else:
            logger.info(f"SMS OTP sent successfully to {formatted_phone}: {sms_message}")
        
        return verification, otp_code, sms_success, sms_message
    
    @staticmethod
    def verify_otp(user, otp_code):
        """Verify OTP code"""
        try:
            # Get latest verification for this user
            verification = PhoneVerification.objects.filter(
                user=user,
                otp_code=otp_code
            ).latest('created_at')
            
            # Check if valid and not expired
            if verification.is_valid():
                # Mark as verified
                verification.is_verified = True
                verification.save()
                
                # Update user's phone_verified status and phone number
                user.phone_verified = True
                user.phone = verification.phone_number  # Update the phone field
                user.save()
                
                return True, "Phone verified successfully!"
            else:
                return False, "Invalid or expired OTP"
                
        except PhoneVerification.DoesNotExist:
            return False, "Invalid OTP code"
    
    @staticmethod
    def get_user_verification_status(user):
        """Get user's phone verification status"""
        try:
            latest_verification = PhoneVerification.objects.filter(
                user=user
            ).latest('created_at')
            return latest_verification.is_verified
        except PhoneVerification.DoesNotExist:
            return False
    
    @staticmethod
    def normalize_phone_to_local(phone_number):
        """
        Normalize phone number to local format
        - Saudi: +966501234567 → 0501234567
        - Pakistan: +923076900096 → 03076900096
        
        Args:
            phone_number: Phone number in various formats
            
        Returns:
            str: Normalized phone number in local format
        """
        # Remove all non-digit characters except +
        digits = ''.join(filter(str.isdigit, phone_number))
        
        # Handle Saudi Arabia numbers
        if digits.startswith('9665') and len(digits) >= 12:
            # Has Saudi country code: 9665xxxxxxxx -> 05xxxxxxxx
            return '0' + digits[3:]
        elif digits.startswith('5') and len(digits) == 9:
            # Saudi without leading 0: 5xxxxxxxx -> 05xxxxxxxx
            return '0' + digits
        elif digits.startswith('05') and len(digits) == 10:
            # Already in Saudi local format: 05xxxxxxxx
            return digits
        # Handle Pakistan numbers
        elif digits.startswith('923') and len(digits) >= 12:
            # Has Pakistan country code: 923xxxxxxxxx -> 03xxxxxxxxx
            return '0' + digits[2:]
        elif digits.startswith('3') and len(digits) == 10:
            # Pakistan without leading 0: 3xxxxxxxxx -> 03xxxxxxxxx
            return '0' + digits
        elif digits.startswith('03') and len(digits) == 11:
            # Already in Pakistan local format: 03xxxxxxxxx
            return digits
        else:
            # Return as is if format is unclear
            return phone_number
    
    @staticmethod
    def create_verification_for_phone(phone_number, user=None):
        """
        Create phone verification for phone-based authentication.
        If user is not provided, finds or creates a minimal user.
        
        Args:
            phone_number: Phone number to verify
            user: Optional user object. If None, will find or create user by phone.
            
        Returns:
            tuple: (verification, otp_code, sms_success, sms_message, user)
        """
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Normalize phone to local format for database
        local_phone = PhoneVerificationService.normalize_phone_to_local(phone_number)
        
        # Format phone for SMS (E.164 format)
        from .twilio_service import TwilioSMSService
        formatted_phone = TwilioSMSService.format_phone_number(phone_number)
        
        # Test phone numbers for development/testing (bypass SMS, use fixed OTP)
        TEST_PHONES = ['0500000000', '0510000001', '0599999999', '0511111111', '0511111112', "0511111113", "0511111114", "0511111115"]
        TEST_OTP = '123456'
        
        # Check if it's a test phone number
        if local_phone in TEST_PHONES:
            # Find or create user
            if user is None:
                user = User.objects.filter(phone=local_phone).first()
                if not user:
                    # Create minimal user for phone verification
                    username = f"user_{local_phone}"
                    counter = 1
                    while User.objects.filter(username=username).exists():
                        username = f"user_{local_phone}_{counter}"
                        counter += 1
                    
                    try:
                        user = User.objects.create_user(
                            username=username,
                            phone=local_phone,
                            email=None,  # Explicitly set to None to avoid unique constraint issues
                            is_active=True
                        )
                    except Exception as e:
                        # If unique constraint fails, try to find existing user or handle gracefully
                        if 'UNIQUE constraint' in str(e) and 'email' in str(e):
                            logger.warning(f"Email constraint issue detected for phone {local_phone}. Attempting to find existing user...")
                            # Try to find user by phone instead
                            user = User.objects.filter(phone=local_phone).first()
                            if not user:
                                # If still can't find, try to clean up and retry (only if not in test transaction)
                                from django.db import connection
                                if not connection.in_atomic_block:
                                    try:
                                        User.objects.filter(email='').update(email=None)
                                        user = User.objects.create_user(
                                            username=username,
                                            phone=local_phone,
                                            email=None,
                                            is_active=True
                                        )
                                    except Exception as retry_error:
                                        logger.error(f"Failed to create user after cleanup: {retry_error}")
                                        raise Exception(f"Failed to create user: {retry_error}")
                                else:
                                    # In transaction, just raise the original error
                                    raise
                        else:
                            raise
            
            # Create verification with test OTP (no SMS sent)
            otp_code = TEST_OTP
            expires_at = timezone.now() + timedelta(minutes=5)
            
            verification = PhoneVerification.objects.create(
                user=user,
                phone_number=formatted_phone,
                otp_code=otp_code,
                expires_at=expires_at
            )
            
            # Log test OTP for visibility
            logger.info(f"🧪 TEST MODE: OTP for {local_phone} is {TEST_OTP}")
            print(f"\n🧪 TEST MODE: OTP for {local_phone} is {TEST_OTP}\n")
            
            return verification, otp_code, True, f"Test mode - OTP: {TEST_OTP}", user
        
        # Find or create user for real phone numbers
        if user is None:
            user = User.objects.filter(phone=local_phone).first()
            if not user:
                # Create minimal user for phone verification
                # Generate unique username from phone
                username = f"user_{local_phone}"
                # Ensure username is unique
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"user_{local_phone}_{counter}"
                    counter += 1
                
                try:
                    user = User.objects.create_user(
                        username=username,
                        phone=local_phone,
                        email=None,  # Explicitly set to None to avoid unique constraint issues
                        is_active=True
                    )
                except Exception as e:
                    # If unique constraint fails, try to find existing user by phone
                    if 'UNIQUE constraint' in str(e) and 'email' in str(e):
                        logger.warning(f"Email constraint issue detected for phone {local_phone}. Attempting to find existing user...")
                        # Try to find user by phone instead (most likely case)
                        user = User.objects.filter(phone=local_phone).first()
                        if not user:
                            # If user doesn't exist, the email constraint is from a different user
                            # Just re-raise - this shouldn't happen in normal flow
                            logger.error(f"Email constraint error but no user found for phone {local_phone}")
                            raise
                    else:
                        raise
        
        # Use Twilio Verify API for real phone numbers
        from .twilio_service import TwilioSMSService
        
        # Detect locale based on country code
        # Saudi Arabia (+966) -> Arabic (ar)
        # Pakistan (+92) -> English (en) or Urdu (ur)
        if formatted_phone.startswith('+966'):
            locale = 'ar'  # Arabic for Saudi Arabia
        elif formatted_phone.startswith('+92'):
            locale = 'en'  # English for Pakistan (can also use 'ur' for Urdu)
        else:
            locale = 'en'  # Default to English
        
        sms_success, sms_message, verification_sid = TwilioSMSService.send_verification_code(
            phone_number=formatted_phone,
            locale=locale
        )
        
        if sms_success:
            # Create verification record with Twilio Verify SID
            expires_at = timezone.now() + timedelta(minutes=10)  # Twilio Verify codes expire in 10 minutes
            
            verification = PhoneVerification.objects.create(
                user=user,
                phone_number=formatted_phone,
                otp_code=None,  # No OTP code stored when using Twilio Verify
                verification_sid=verification_sid,
                expires_at=expires_at
            )
            
            logger.info(f"Twilio Verify code sent. Verification SID: {verification_sid}, To: {formatted_phone}")
            return verification, None, sms_success, sms_message, user
        else:
            # If Twilio Verify fails, log error but still create verification record for tracking
            expires_at = timezone.now() + timedelta(minutes=5)
            verification = PhoneVerification.objects.create(
                user=user,
                phone_number=formatted_phone,
                otp_code=None,
                verification_sid=None,
                expires_at=expires_at
            )
            logger.error(f"Failed to send Twilio Verify code: {sms_message}")
            return verification, None, sms_success, sms_message, user
    
    @staticmethod
    def verify_otp_for_phone(phone_number, otp_code):
        """
        Verify OTP for phone-based authentication.
        Finds user by phone and verifies OTP.
        Uses Twilio Verify API for real phones, manual verification for test phones.
        
        Args:
            phone_number: Phone number
            otp_code: OTP code to verify
            
        Returns:
            tuple: (is_valid: bool, message: str, user: User or None)
        """
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Normalize phone number to local format
        local_phone = PhoneVerificationService.normalize_phone_to_local(phone_number)
        
        # Format phone for Twilio Verify (E.164 format)
        from .twilio_service import TwilioSMSService
        formatted_phone = TwilioSMSService.format_phone_number(phone_number)
        
        # Test phone numbers - use manual verification
        TEST_PHONES = ['0500000000', '0510000001', '0599999999', '0511111111', '0511111112', "0511111113", "0511111114", "0511111115"]
        
        if local_phone in TEST_PHONES:
            # Manual verification for test phones
            user = User.objects.filter(phone=local_phone).first()
            if not user:
                return False, "User not found for this phone number", None
            
            # Verify OTP - get latest verification for this user
            try:
                verification = PhoneVerification.objects.filter(
                    user=user,
                    otp_code=otp_code
                ).latest('created_at')
                
                # Check if valid and not expired
                if verification.is_valid():
                    # Mark as verified
                    verification.is_verified = True
                    verification.save()
                    
                    # Update user's phone_verified status
                    user.phone_verified = True
                    if not user.phone or user.phone != local_phone:
                        user.phone = local_phone
                    user.save()
                    
                    return True, "Phone verified successfully!", user
                else:
                    return False, "Invalid or expired OTP", None
                    
            except PhoneVerification.DoesNotExist:
                return False, "Invalid OTP code", None
        else:
            # Use Twilio Verify API for real phone numbers
            user = User.objects.filter(phone=local_phone).first()
            if not user:
                return False, "User not found for this phone number", None
            
            # Verify using Twilio Verify API
            is_valid, message = TwilioSMSService.verify_code(
                phone_number=formatted_phone,
                code=otp_code
            )
            
            if is_valid:
                # Mark verification as verified in database
                try:
                    verification = PhoneVerification.objects.filter(
                        user=user,
                        verification_sid__isnull=False
                    ).latest('created_at')
                    verification.is_verified = True
                    verification.save()
                except PhoneVerification.DoesNotExist:
                    # Create verification record if doesn't exist
                    expires_at = timezone.now() + timedelta(minutes=10)
                    verification = PhoneVerification.objects.create(
                        user=user,
                        phone_number=formatted_phone,
                        verification_sid=None,  # Already verified by Twilio
                        is_verified=True,
                        expires_at=expires_at
                    )
                
                # Update user's phone_verified status
                user.phone_verified = True
                if not user.phone or user.phone != local_phone:
                    user.phone = local_phone
                user.save()
                
                return True, message, user
            else:
                return False, message, None

