import random
import logging
import uuid
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.hashers import check_password, make_password
from .models import PhoneVerification
from .phone_format import format_phone_e164, normalize_phone_to_local, phone_lookup_variations
from .otp_session import (
    MAX_RESEND_PER_HOUR,
    MAX_VERIFY_ATTEMPTS,
    RESEND_COOLDOWN_SECONDS,
    OtpErrorCode,
    OtpRateLimitError,
    OtpResendCooldownError,
    OtpVerifyResult,
    OTP_ERROR_MESSAGES,
    build_session_payload,
    mask_phone,
    otp_expiry_minutes,
)
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

        user = User.objects.filter(phone__in=phone_lookup_variations(local_phone)).first()
        if user:
            if user.phone != local_phone:
                user.phone = local_phone
                user.save(update_fields=['phone'])
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
    def _log_otp_event(event, phone_e164, session_id, result, **extra):
        from django.conf import settings

        payload = {
            'event': event,
            'phone': mask_phone(phone_e164),
            'verification_id': str(session_id) if session_id else None,
            'result': result,
            'environment': getattr(settings, 'APP_ENV', 'unknown'),
            **extra,
        }
        logger.info('OTP session event: %s', payload)

    @staticmethod
    def _invalidate_pending_sessions(phone_e164):
        PhoneVerification.objects.filter(
            phone_number=phone_e164,
            is_verified=False,
            invalidated_at__isnull=True,
        ).update(invalidated_at=timezone.now())

    @staticmethod
    def _hourly_session_count(phone_e164) -> int:
        since = timezone.now() - timedelta(hours=1)
        return PhoneVerification.objects.filter(
            phone_number=phone_e164,
            created_at__gte=since,
        ).count()

    @staticmethod
    def _check_resend_rate_limit(phone_e164):
        if PhoneVerificationService._hourly_session_count(phone_e164) >= MAX_RESEND_PER_HOUR:
            return OtpVerifyResult.fail(OtpErrorCode.RATE_LIMITED, status_code=429)
        return None

    @staticmethod
    def _get_active_resend_cooldown(phone_e164):
        latest = (
            PhoneVerification.objects.filter(
                phone_number=phone_e164,
                is_verified=False,
                invalidated_at__isnull=True,
            )
            .order_by('-created_at')
            .first()
        )
        if not latest or not latest.resend_available_at:
            return None
        if timezone.now() >= latest.resend_available_at:
            return None
        return latest

    @staticmethod
    def _create_phone_session(*, user, formatted_phone, locale, is_test_phone=False):
        sms_lang = taqnyat_sms_language(locale)
        expires_at = timezone.now() + timedelta(minutes=otp_expiry_minutes())
        resend_available_at = timezone.now() + timedelta(seconds=RESEND_COOLDOWN_SECONDS)

        if is_test_phone:
            otp_hash = make_password(PhoneVerificationService.TEST_OTP)
            verification = PhoneVerification.objects.create(
                user=user,
                phone_number=formatted_phone,
                otp_code=None,
                otp_hash=otp_hash,
                expires_at=expires_at,
                resend_available_at=resend_available_at,
            )
            PhoneVerificationService._log_otp_event(
                'otp_sent',
                formatted_phone,
                verification.session_id,
                'success',
                otp_expires_at=verification.expires_at.isoformat(),
                test_mode=True,
            )
            return verification, PhoneVerificationService.TEST_OTP, True, 'OTP sent successfully', user

        request_id = str(uuid.uuid4())
        verification = PhoneVerification.objects.create(
            user=user,
            phone_number=formatted_phone,
            otp_code=None,
            verification_sid=request_id,
            expires_at=expires_at,
            resend_available_at=resend_available_at,
        )

        from .tasks import send_verification_code_task
        send_verification_code_task.delay(
            phone_number=formatted_phone,
            locale=sms_lang,
            verification_id=verification.id,
        )

        PhoneVerificationService._log_otp_event(
            'otp_sent',
            formatted_phone,
            verification.session_id,
            'success',
            otp_expires_at=verification.expires_at.isoformat(),
            attempt_count=0,
        )
        return verification, None, True, 'Verification code is being sent', user

    @staticmethod
    def create_verification_for_phone(phone_number, user=None, locale=None, enforce_resend_cooldown=False):
        """
        Create phone verification for phone-based authentication.
        Uses Taqnyat Verify for real numbers and a fixed OTP for test numbers.
        """
        local_phone = PhoneVerificationService.normalize_phone_to_local(phone_number)
        formatted_phone = format_phone_e164(phone_number)

        rate_limit = PhoneVerificationService._check_resend_rate_limit(formatted_phone)
        if rate_limit:
            PhoneVerificationService._log_otp_event(
                'otp_send',
                formatted_phone,
                None,
                'rate_limited',
            )
            raise OtpRateLimitError(rate_limit.message, rate_limit.error_code)

        if enforce_resend_cooldown:
            cooldown_session = PhoneVerificationService._get_active_resend_cooldown(formatted_phone)
            if cooldown_session:
                PhoneVerificationService._log_otp_event(
                    'otp_resend',
                    formatted_phone,
                    cooldown_session.session_id,
                    'resend_cooldown',
                )
                raise OtpResendCooldownError(
                    OTP_ERROR_MESSAGES[OtpErrorCode.RESEND_COOLDOWN],
                    OtpErrorCode.RESEND_COOLDOWN,
                    build_session_payload(cooldown_session),
                )

        PhoneVerificationService._invalidate_pending_sessions(formatted_phone)

        if local_phone in PhoneVerificationService.TEST_PHONES:
            user = PhoneVerificationService._find_or_create_user(local_phone, user)
            return PhoneVerificationService._create_phone_session(
                user=user,
                formatted_phone=formatted_phone,
                locale=locale,
                is_test_phone=True,
            )

        user = PhoneVerificationService._find_or_create_user(local_phone, user)
        return PhoneVerificationService._create_phone_session(
            user=user,
            formatted_phone=formatted_phone,
            locale=locale,
            is_test_phone=False,
        )

    @staticmethod
    def _get_verification_session(*, verification_id=None, phone_number=None):
        if verification_id:
            try:
                return PhoneVerification.objects.get(session_id=verification_id)
            except PhoneVerification.DoesNotExist:
                return None

        if not phone_number:
            return None

        local_phone = PhoneVerificationService.normalize_phone_to_local(phone_number)
        formatted_phone = format_phone_e164(phone_number)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.filter(phone__in=phone_lookup_variations(local_phone)).first()
        if not user:
            return None

        return (
            PhoneVerification.objects.filter(
                user=user,
                is_verified=False,
                invalidated_at__isnull=True,
            )
            .order_by('-created_at')
            .first()
        )

    @staticmethod
    def _mark_user_phone_verified(user, local_phone):
        user.phone_verified = True
        if not user.phone or user.phone != local_phone:
            user.phone = local_phone
        user.save()

    @staticmethod
    def verify_otp_for_phone(phone_number=None, otp_code=None, locale=None, verification_id=None):
        """
        Verify OTP for phone-based authentication.
        Prefer verification_id; phone is supported for backward compatibility.
        """
        from django.contrib.auth import get_user_model
        User = get_user_model()

        verification = PhoneVerificationService._get_verification_session(
            verification_id=verification_id,
            phone_number=phone_number,
        )
        if not verification:
            PhoneVerificationService._log_otp_event(
                'otp_verify',
                format_phone_e164(phone_number) if phone_number else '',
                verification_id,
                'no_session',
            )
            return OtpVerifyResult.fail(OtpErrorCode.SESSION_NOT_FOUND)

        formatted_phone = verification.phone_number
        local_phone = normalize_phone_to_local(formatted_phone)
        user = verification.user

        if verification.is_verified:
            return OtpVerifyResult.fail(OtpErrorCode.SESSION_NOT_FOUND)

        if verification.is_invalidated():
            return OtpVerifyResult.fail(OtpErrorCode.SESSION_NOT_FOUND)

        if verification.is_expired():
            PhoneVerificationService._log_otp_event(
                'otp_verify',
                formatted_phone,
                verification.session_id,
                'expired',
                attempt_count=verification.attempt_count,
            )
            return OtpVerifyResult.fail(OtpErrorCode.EXPIRED)

        if verification.attempt_count >= MAX_VERIFY_ATTEMPTS:
            return OtpVerifyResult.fail(OtpErrorCode.MAX_ATTEMPTS, status_code=429)

        sms_lang = taqnyat_sms_language(locale)
        is_test_phone = local_phone in PhoneVerificationService.TEST_PHONES

        if is_test_phone:
            if not verification.otp_hash or not check_password(otp_code, verification.otp_hash):
                verification.attempt_count += 1
                verification.save(update_fields=['attempt_count'])
                PhoneVerificationService._log_otp_event(
                    'otp_verify',
                    formatted_phone,
                    verification.session_id,
                    'wrong_code',
                    attempt_count=verification.attempt_count,
                )
                if verification.attempt_count >= MAX_VERIFY_ATTEMPTS:
                    return OtpVerifyResult.fail(OtpErrorCode.MAX_ATTEMPTS, status_code=429)
                return OtpVerifyResult.fail(OtpErrorCode.INVALID)

            verification.is_verified = True
            verification.save(update_fields=['is_verified'])
            PhoneVerificationService._mark_user_phone_verified(user, local_phone)
            PhoneVerificationService._log_otp_event(
                'otp_verify',
                formatted_phone,
                verification.session_id,
                'success',
                attempt_count=verification.attempt_count,
            )
            return OtpVerifyResult.ok('Phone verified successfully!', user)

        if not verification.verification_sid:
            return OtpVerifyResult.fail(OtpErrorCode.SESSION_NOT_FOUND)

        is_valid, message = TaqnyatVerifyService.verify_code(
            phone_number=formatted_phone,
            request_id=verification.verification_sid,
            code=otp_code,
            lang=sms_lang,
        )

        if is_valid:
            verification.is_verified = True
            verification.save(update_fields=['is_verified'])
            PhoneVerificationService._mark_user_phone_verified(user, local_phone)
            PhoneVerificationService._log_otp_event(
                'otp_verify',
                formatted_phone,
                verification.session_id,
                'success',
                attempt_count=verification.attempt_count,
            )
            return OtpVerifyResult.ok(message or 'Phone verified successfully!', user)

        verification.attempt_count += 1
        verification.save(update_fields=['attempt_count'])
        PhoneVerificationService._log_otp_event(
            'otp_verify',
            formatted_phone,
            verification.session_id,
            'wrong_code',
            attempt_count=verification.attempt_count,
        )

        if verification.attempt_count >= MAX_VERIFY_ATTEMPTS:
            return OtpVerifyResult.fail(OtpErrorCode.MAX_ATTEMPTS, status_code=429)

        if 'expired' in (message or '').lower():
            return OtpVerifyResult.fail(OtpErrorCode.EXPIRED)

        return OtpVerifyResult.fail(OtpErrorCode.INVALID)
