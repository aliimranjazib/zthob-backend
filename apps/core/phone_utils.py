"""Shared helpers for displaying phone numbers in API responses."""

from apps.core.twilio_service import TwilioSMSService


def format_phone_for_display(phone):
    """Return E.164 phone numbers for API responses while keeping DB storage local."""
    if phone is None:
        return phone

    phone_text = str(phone).strip()
    if not phone_text:
        return phone_text

    return TwilioSMSService.format_phone_number(phone_text)


def display_user_label(user):
    """Prefer full name, then formatted phone, then username."""
    if not user:
        return 'Unknown'

    full_name = user.get_full_name().strip()
    if full_name:
        return full_name

    if getattr(user, 'phone', None):
        return format_phone_for_display(user.phone)

    return user.username
