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
            logger.error(f"Failed to send SMS OTP: {sms_message}")
        
        return verification, otp_code
    
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

