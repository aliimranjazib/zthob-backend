"""Phone number formatting helpers for Saudi Arabia numbers."""


def format_phone_e164(phone_number: str) -> str:
    """
    Format a Saudi phone number to E.164 (+9665xxxxxxxx).

    Accepts: 0501234567, 501234567, 966501234567, +966501234567
    """
    digits = ''.join(filter(str.isdigit, phone_number))

    if phone_number.startswith('+') and digits.startswith('966'):
        return '+' + digits

    if digits.startswith('05') and len(digits) == 10:
        return '+966' + digits[1:]
    if digits.startswith('5') and len(digits) == 9:
        return '+966' + digits
    if digits.startswith('966') and len(digits) >= 12:
        return '+' + digits

    return '+' + digits if digits else phone_number


def format_phone_for_taqnyat(phone_number: str) -> str:
    """Format phone for Taqnyat API: 966501234567 (no + prefix)."""
    e164 = format_phone_e164(phone_number)
    return e164.lstrip('+')


def normalize_phone_to_local(phone_number: str) -> str:
    """Normalize to Saudi local format: 0501234567."""
    digits = ''.join(filter(str.isdigit, phone_number))

    if digits.startswith('9665') and len(digits) >= 12:
        return '0' + digits[3:]
    if digits.startswith('5') and len(digits) == 9:
        return '0' + digits
    if digits.startswith('05') and len(digits) == 10:
        return digits

    return phone_number


def phone_lookup_variations(phone_number: str) -> list[str]:
    """
    Return common phone string variants used in the database for lookups.

    POS, login, and legacy records may store the same number as 05..., +966..., etc.
    """
    local = normalize_phone_to_local(phone_number)
    e164 = format_phone_e164(phone_number)
    stripped = e164.lstrip('+')

    variations = {local, e164, stripped, f'+{stripped}'}
    if local.startswith('0') and len(local) == 10:
        without_zero = local[1:]
        variations.update(
            {
                without_zero,
                f'966{without_zero}',
                f'+966{without_zero}',
            }
        )

    return sorted(v for v in variations if v)


def is_valid_saudi_phone(value: str) -> bool:
    """Return True if value is a valid Saudi mobile number."""
    phone = value.strip().replace(' ', '').replace('-', '')
    digits = ''.join(filter(str.isdigit, phone))

    if phone.startswith('+9665') and len(digits) >= 12:
        return True
    if digits.startswith('05') and len(digits) == 10:
        return True
    if digits.startswith('5') and len(digits) == 9:
        return True
    if digits.startswith('9665') and len(digits) >= 12:
        return True
    return False
