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
        Normalize phone number to local format (05xxxxxxxx)
        
        Args:
            phone_number: Phone number in various formats
            
        Returns:
            str: Normalized phone number in local format
        """
        # Remove all non-digit characters except +
        digits = ''.join(filter(str.isdigit, phone_number))
        
        # Convert to local format (05xxxxxxxx)
        if digits.startswith('9665') and len(digits) >= 12:
            # Has country code: 9665xxxxxxxx -> 05xxxxxxxx
            return '0' + digits[3:]
        elif digits.startswith('5') and len(digits) == 9:
            # Without leading 0: 5xxxxxxxx -> 05xxxxxxxx
            return '0' + digits
        elif digits.startswith('05') and len(digits) == 10:
            # Already in local format: 05xxxxxxxx
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
        TEST_PHONES = ['0500000000', '0510000001', '0599999999','0511111112',"0511111113","0511111114","0511111115"]
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
                    
                    user = User.objects.create_user(
                        username=username,
                        phone=local_phone,
                        email=None,  # Explicitly set to None to avoid unique constraint issues
                        is_active=True
                    )
            
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
                
                user = User.objects.create_user(
                    username=username,
                    phone=local_phone,
                    email=None,  # Explicitly set to None to avoid unique constraint issues
                    is_active=True
                )
        
        # Create verification using existing method (sends real SMS)
        verification, otp_code, sms_success, sms_message = PhoneVerificationService.create_verification(
            user=user,
            phone_number=formatted_phone
        )
        
        return verification, otp_code, sms_success, sms_message, user
    
    @staticmethod
    def verify_otp_for_phone(phone_number, otp_code):
        """
        Verify OTP for phone-based authentication.
        Finds user by phone and verifies OTP.
        
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
        
        # Find user by phone
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
                # Ensure phone is set correctly (use phone from verification if different)
                if verification.phone_number:
                    # Extract local format from verification phone_number (which is in E.164)
                    verif_phone = verification.phone_number.replace('+966', '0')
                    if verif_phone != local_phone:
                        local_phone = verif_phone
                if not user.phone or user.phone != local_phone:
                    user.phone = local_phone
                user.save()
                
                return True, "Phone verified successfully!", user
            else:
                return False, "Invalid or expired OTP", None
                
        except PhoneVerification.DoesNotExist:
            return False, "Invalid OTP code", None

