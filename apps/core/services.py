import random
from django.utils import timezone
from datetime import timedelta
from .models import PhoneVerification

class PhoneVerificationService:
    """Reusable service for phone verification"""
    
    @staticmethod
    def generate_otp():
        """Generate 6-digit OTP"""
        return str(random.randint(100000, 999999))
    
    @staticmethod
    def create_verification(user, phone_number):
        """Create new phone verification record"""
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
                
                # Update user's phone_verified status
                user.phone_verified = True
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

