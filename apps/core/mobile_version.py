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

MOBILE_VERSION_CACHE_PREFIX = 'mobile_version_policy_v2'
MOBILE_VERSION_CACHE_TTL = 60 * 60 * 24  # 24 hours
REQUIRED_POLICY_KEYS = frozenset({'latest_version', 'soft_update_enabled', 'force_update_enabled'})


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
        'latest_version': policy.latest_version,
        'soft_update_enabled': policy.soft_update_enabled,
        'force_update_enabled': policy.force_update_enabled,
    }


def normalize_policy(policy) -> dict | None:
    """Return policy dict when cache payload matches the current schema."""
    if not policy or not isinstance(policy, dict):
        return None
    if not REQUIRED_POLICY_KEYS.issubset(policy.keys()):
        return None
    return policy


def get_version_policy(app: str, platform: str) -> dict | None:
    """Load active version policy from Redis cache or database."""
    from apps.core.models import MobileAppVersionPolicy

    cache_key = mobile_version_cache_key(app, platform)
    cached = cache.get(cache_key)
    normalized = normalize_policy(cached)
    if normalized is not None:
        return normalized
    if cached is not None:
        cache.delete(cache_key)

    policy = MobileAppVersionPolicy.objects.filter(
        app=app,
        platform=platform,
        is_active=True,
    ).first()

    payload = policy_to_dict(policy) if policy else None
    cache.set(cache_key, payload, MOBILE_VERSION_CACHE_TTL)
    return payload


def evaluate_mobile_version(app: str, platform: str, current_version: str) -> dict:
    """Return soft/force update flags for a mobile client."""
    no_update = {'soft_update': False, 'force_update': False}

    policy = get_version_policy(app, platform)
    if not policy:
        return no_update

    latest_version = policy.get('latest_version')
    if not latest_version or compare_versions(current_version, latest_version) >= 0:
        return no_update

    if policy.get('force_update_enabled'):
        return {'soft_update': False, 'force_update': True}

    if policy.get('soft_update_enabled'):
        return {'soft_update': True, 'force_update': False}

    return no_update
