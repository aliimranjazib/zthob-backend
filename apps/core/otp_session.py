"""OTP session constants, error codes, and helpers for phone auth."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from django.conf import settings

OTP_LENGTH = 4
RESEND_COOLDOWN_SECONDS = 60
MAX_VERIFY_ATTEMPTS = 5
MAX_RESEND_PER_HOUR = 10


def otp_expiry_minutes() -> int:
    return int(getattr(settings, 'OTP_EXPIRY_MINUTES', 5))


def otp_expiry_seconds() -> int:
    return otp_expiry_minutes() * 60


class OtpErrorCode:
    INVALID = 'OTP_INVALID'
    EXPIRED = 'OTP_EXPIRED'
    SESSION_NOT_FOUND = 'OTP_SESSION_NOT_FOUND'
    MAX_ATTEMPTS = 'OTP_MAX_ATTEMPTS'
    RESEND_COOLDOWN = 'OTP_RESEND_COOLDOWN'
    RATE_LIMITED = 'OTP_RATE_LIMITED'
    PHONE_INVALID = 'PHONE_INVALID'


OTP_ERROR_MESSAGES = {
    OtpErrorCode.INVALID: 'Invalid verification code',
    OtpErrorCode.EXPIRED: 'Code expired. Request a new one',
    OtpErrorCode.SESSION_NOT_FOUND: 'No active verification. Request a new code',
    OtpErrorCode.MAX_ATTEMPTS: 'Too many attempts. Try again later',
    OtpErrorCode.RESEND_COOLDOWN: 'Please wait before requesting another code',
    OtpErrorCode.RATE_LIMITED: 'Too many requests for this number',
    OtpErrorCode.PHONE_INVALID: 'Invalid phone number',
}


@dataclass
class OtpVerifyResult:
    success: bool
    message: str
    user: Optional[object] = None
    error_code: Optional[str] = None
    status_code: int = 400

    @classmethod
    def ok(cls, message: str, user):
        return cls(success=True, message=message, user=user, status_code=200)

    @classmethod
    def fail(cls, error_code: str, status_code: int = 400, message: str | None = None):
        return cls(
            success=False,
            message=message or OTP_ERROR_MESSAGES.get(error_code, 'Verification failed'),
            user=None,
            error_code=error_code,
            status_code=status_code,
        )


def mask_phone(phone_e164: str) -> str:
    """Mask phone for logs: +9665****1234"""
    digits = ''.join(ch for ch in phone_e164 if ch.isdigit())
    if len(digits) < 8:
        return phone_e164
    return f"+{digits[:4]}****{digits[-4:]}"


def build_session_payload(verification) -> dict:
    from django.utils import timezone

    expires_in = max(0, int((verification.expires_at - timezone.now()).total_seconds()))
    resend_after = RESEND_COOLDOWN_SECONDS
    if verification.resend_available_at:
        resend_after = max(
            0,
            int((verification.resend_available_at - timezone.now()).total_seconds()),
        )

    return {
        'verification_id': str(verification.session_id),
        'expires_in': expires_in,
        'resend_after': resend_after,
        'otp_length': OTP_LENGTH,
    }


class OtpRateLimitError(Exception):
    def __init__(self, message: str, error_code: str = OtpErrorCode.RATE_LIMITED):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


class OtpResendCooldownError(Exception):
    def __init__(self, message: str, error_code: str, session_payload: dict):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.session_payload = session_payload
