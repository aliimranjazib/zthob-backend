import random
import logging
import uuid
from django.utils import timezone
from datetime import timedelta
from .models import PhoneVerification
from .phone_format import format_phone_e164, normalize_phone_to_local
from zthob.languages import taqnyat_sms_language
from .taqnyat_service import TaqnyatVerifyService

logger = logging.getLogger(__name__)

class PhoneVerificationService:
    """Reusable service for phone verification"""
    
    # Test phone numbers for development/testing (bypass SMS, use fixed OTP)
    TEST_PHONES = [
        '0500000000', '0510000001', '0599999999', '0511111111', '0511111112', 
        "0511111113", "0511111114", "0511111115", "0500000001", "0500000002", 
        "0500000003", "0500000004", "0500000005", "0500000006", "0500000007", 
        "0500000008", "0500000009", "0522222220", "0522222221","0522222222",
        "0522222223", "0522222224", "0522222225", "0522222226", "0522222227",
        "0522222228", "0522222229", "0522222230"
    ]
    TEST_OTP = '1234'
    
    @staticmethod
    def generate_otp():
        """Generate 4-digit OTP"""
        return str(random.randint(1000, 9999))
    
    @staticmethod
    def create_verification(user, phone_number):
        """Create new phone verification record and send OTP via SMS"""
        otp_code = PhoneVerificationService.generate_otp()
        expires_at = timezone.now() + timedelta(minutes=5)
        
        verification = PhoneVerification.objects.create(
            user=user,
            phone_number=phone_number,
            otp_code=otp_code,
            expires_at=expires_at
        )
        
        from .tasks import send_otp_sms_task
        send_otp_sms_task.delay(phone_number=phone_number, otp_code=otp_code)
        
        logger.info(f"Queued SMS OTP task for {phone_number}")
        
        return verification, otp_code, True, "OTP is being sent"
    
    @staticmethod
    def verify_otp(user, otp_code):
        """Verify OTP code"""
        try:
            verification = PhoneVerification.objects.filter(
                user=user,
                otp_code=otp_code
            ).latest('created_at')
            
            if verification.is_valid():
                verification.is_verified = True
                verification.save()
                
                user.phone_verified = True
                user.phone = verification.phone_number
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
        """Normalize phone number to Saudi local format (0501234567)."""
        return normalize_phone_to_local(phone_number)
    
    @staticmethod
    def _find_or_create_user(local_phone, user=None):
        from django.contrib.auth import get_user_model
        User = get_user_model()

        if user is not None:
            return user

        user = User.objects.filter(phone=local_phone).first()
        if user:
            return user

        username = f"user_{local_phone}"
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"user_{local_phone}_{counter}"
            counter += 1

        try:
            return User.objects.create_user(
                username=username,
                phone=local_phone,
                email=None,
                is_active=True,
            )
        except Exception as e:
            if 'UNIQUE constraint' in str(e) and 'email' in str(e):
                logger.warning(
                    "Email constraint issue for phone %s. Finding existing user.",
                    local_phone,
                )
                user = User.objects.filter(phone=local_phone).first()
                if user:
                    return user
                from django.db import connection
                if not connection.in_atomic_block:
                    User.objects.filter(email='').update(email=None)
                    return User.objects.create_user(
                        username=username,
                        phone=local_phone,
                        email=None,
                        is_active=True,
                    )
            raise

    @staticmethod
    def create_verification_for_phone(phone_number, user=None, locale=None):
        """
        Create phone verification for phone-based authentication.
        Uses Taqnyat Verify for real numbers and a fixed OTP for test numbers.
        """
        sms_lang = taqnyat_sms_language(locale)
        local_phone = PhoneVerificationService.normalize_phone_to_local(phone_number)
        formatted_phone = format_phone_e164(phone_number)

        if local_phone in PhoneVerificationService.TEST_PHONES:
            user = PhoneVerificationService._find_or_create_user(local_phone, user)
            otp_code = PhoneVerificationService.TEST_OTP
            expires_at = timezone.now() + timedelta(minutes=5)

            verification = PhoneVerification.objects.create(
                user=user,
                phone_number=formatted_phone,
                otp_code=otp_code,
                expires_at=expires_at,
            )

            logger.info("TEST MODE: OTP for %s is %s", local_phone, PhoneVerificationService.TEST_OTP)
            return verification, otp_code, True, f"Test mode - OTP: {PhoneVerificationService.TEST_OTP}", user

        user = PhoneVerificationService._find_or_create_user(local_phone, user)
        request_id = str(uuid.uuid4())
        expires_at = timezone.now() + timedelta(minutes=10)

        verification = PhoneVerification.objects.create(
            user=user,
            phone_number=formatted_phone,
            otp_code=None,
            verification_sid=request_id,
            expires_at=expires_at,
        )

        from .tasks import send_verification_code_task
        send_verification_code_task.delay(
            phone_number=formatted_phone,
            locale=sms_lang,
            verification_id=verification.id,
        )

        logger.info("Queued Taqnyat Verify code task for %s", formatted_phone)
        return verification, None, True, "Verification code is being sent", user
    
    @staticmethod
    def verify_otp_for_phone(phone_number, otp_code, locale=None):
        """
        Verify OTP for phone-based authentication.
        Uses Taqnyat Verify for real phones and manual verification for test phones.
        """
        sms_lang = taqnyat_sms_language(locale)
        from django.contrib.auth import get_user_model
        User = get_user_model()

        local_phone = PhoneVerificationService.normalize_phone_to_local(phone_number)
        formatted_phone = format_phone_e164(phone_number)

        if local_phone in PhoneVerificationService.TEST_PHONES:
            user = User.objects.filter(phone=local_phone).first()
            if not user:
                return False, "User not found for this phone number", None

            try:
                verification = PhoneVerification.objects.filter(
                    user=user,
                    otp_code=otp_code,
                ).latest('created_at')

                if verification.is_valid():
                    verification.is_verified = True
                    verification.save()

                    user.phone_verified = True
                    if not user.phone or user.phone != local_phone:
                        user.phone = local_phone
                    user.save()

                    return True, "Phone verified successfully!", user
                return False, "Invalid or expired OTP", None

            except PhoneVerification.DoesNotExist:
                return False, "Invalid OTP code", None

        user = User.objects.filter(phone=local_phone).first()
        if not user:
            return False, "User not found for this phone number", None

        try:
            verification = PhoneVerification.objects.filter(
                user=user,
                verification_sid__isnull=False,
                is_verified=False,
            ).latest('created_at')
        except PhoneVerification.DoesNotExist:
            return False, "No pending verification found. Please request a new OTP.", None

        is_valid, message = TaqnyatVerifyService.verify_code(
            phone_number=formatted_phone,
            request_id=verification.verification_sid,
            code=otp_code,
            lang=sms_lang,
        )

        if is_valid:
            verification.is_verified = True
            verification.save()

            user.phone_verified = True
            if not user.phone or user.phone != local_phone:
                user.phone = local_phone
            user.save()

            return True, message, user

        return False, message, None
