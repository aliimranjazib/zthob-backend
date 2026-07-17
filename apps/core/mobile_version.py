"""Mobile app version policy lookup and update evaluation."""

from packaging.version import InvalidVersion, Version

from django.core.cache import cache

MOBILE_APP_CUSTOMER = 'customer'
MOBILE_APP_TAILOR = 'tailor'
MOBILE_APP_RIDER = 'rider'

MOBILE_PLATFORM_IOS = 'ios'
MOBILE_PLATFORM_ANDROID = 'android'

MOBILE_APPS = {
    MOBILE_APP_CUSTOMER,
    MOBILE_APP_TAILOR,
    MOBILE_APP_RIDER,
}

MOBILE_PLATFORMS = {
    MOBILE_PLATFORM_IOS,
    MOBILE_PLATFORM_ANDROID,
}

MOBILE_VERSION_CACHE_PREFIX = 'mobile_version_policy'
MOBILE_VERSION_CACHE_TTL = 60 * 60 * 24  # 24 hours


def mobile_version_cache_key(app: str, platform: str) -> str:
    return f'{MOBILE_VERSION_CACHE_PREFIX}:{app}:{platform}'


def clear_mobile_version_cache(app: str | None = None, platform: str | None = None) -> None:
    if app and platform:
        cache.delete(mobile_version_cache_key(app, platform))
        return

    for app_name in MOBILE_APPS:
        for platform_name in MOBILE_PLATFORMS:
            cache.delete(mobile_version_cache_key(app_name, platform_name))


def parse_version(version_string: str) -> Version | None:
    if not version_string:
        return None
    try:
        return Version(version_string.strip())
    except InvalidVersion:
        return None


def compare_versions(current: str, target: str) -> int:
    """
    Compare two semver strings.

    Returns -1 if current < target, 0 if equal, 1 if current > target.
    Invalid versions are treated as 0.0.0.
    """
    current_version = parse_version(current) or Version('0.0.0')
    target_version = parse_version(target) or Version('0.0.0')
    if current_version < target_version:
        return -1
    if current_version > target_version:
        return 1
    return 0


def policy_to_dict(policy) -> dict:
    return {
        'app': policy.app,
        'platform': policy.platform,
        'minimum_version': policy.minimum_version,
        'latest_version': policy.latest_version,
        'force_update_enabled': policy.force_update_enabled,
        'store_url': policy.store_url,
        'update_title_en': policy.update_title_en,
        'update_title_ar': policy.update_title_ar,
        'update_message_en': policy.update_message_en,
        'update_message_ar': policy.update_message_ar,
    }


def get_version_policy(app: str, platform: str) -> dict | None:
    """Load active version policy from Redis cache or database."""
    from apps.core.models import MobileAppVersionPolicy

    cache_key = mobile_version_cache_key(app, platform)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached or None

    policy = MobileAppVersionPolicy.objects.filter(
        app=app,
        platform=platform,
        is_active=True,
    ).first()

    payload = policy_to_dict(policy) if policy else None
    cache.set(cache_key, payload, MOBILE_VERSION_CACHE_TTL)
    return payload


def evaluate_mobile_version(app: str, platform: str, current_version: str, language: str = 'en') -> dict:
    """Return a minimal update decision for a mobile client."""
    policy = get_version_policy(app, platform)
    if not policy:
        return {
            'update_required': False,
            'force_update': False,
        }

    below_minimum = compare_versions(current_version, policy['minimum_version']) < 0
    below_latest = compare_versions(current_version, policy['latest_version']) < 0
    force_update = below_minimum and policy['force_update_enabled']
    update_required = force_update or below_latest

    if not update_required:
        return {
            'update_required': False,
            'force_update': False,
        }

    use_ar = language == 'ar'
    return {
        'update_required': True,
        'force_update': force_update,
        'store_url': policy['store_url'] or None,
        'title': policy['update_title_ar'] if use_ar else policy['update_title_en'],
        'message': policy['update_message_ar'] if use_ar else policy['update_message_en'],
    }
