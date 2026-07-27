"""Supported application languages."""

SUPPORTED_LANGUAGES = ('en', 'ar', 'ur')
DEFAULT_LANGUAGE = 'ar'
TRANSLATABLE_LANGUAGES = ('ar', 'ur')
RTL_LANGUAGES = ('ar', 'ur')
TAQNYAT_SMS_LANGUAGES = ('ar', 'en')


def is_rtl_language(language: str) -> bool:
    return language in RTL_LANGUAGES


def taqnyat_sms_language(language: str | None) -> str:
    """Map app language to Taqnyat Verify/SMS lang (ar|en only)."""
    if language == 'ar' or not language:
        return 'ar'
    return 'en'
