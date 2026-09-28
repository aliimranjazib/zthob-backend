"""Opt-in DRF rate limits for authentication endpoints only.

App APIs (orders, fabrics, shops, etc.) are not throttled at the DRF layer.
OTP endpoints also rely on PhoneVerificationService limits (resend cooldown, hourly cap).
"""

from rest_framework.throttling import AnonRateThrottle


class OTPRateThrottle(AnonRateThrottle):
    """Phone login, verify, and resend OTP — keyed by client IP."""

    scope = 'otp'


class AuthLoginRateThrottle(AnonRateThrottle):
    """Username/password login attempts — keyed by client IP."""

    scope = 'auth_login'
