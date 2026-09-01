"""Helpers for rider customer field APIs."""

from django.contrib.auth import get_user_model
from rest_framework import status

from apps.customization.models import UserStylePreset
from apps.orders.measurement_utils import has_measurement_values, public_measurements
from apps.riders.models import RiderProfile
from apps.tailors.services.pos_customer_styles import get_customer_style_presets
from zthob.utils import api_response

User = get_user_model()


def require_approved_rider(request):
    """
    Validate authenticated approved rider.

    Returns (rider_profile, None) on success or (None, error_response) on failure.
    """
    if not request.user.is_rider:
        return None, api_response(
            success=False,
            message='Only riders can access this endpoint',
            status_code=status.HTTP_403_FORBIDDEN,
        )

    try:
        rider_profile = RiderProfile.objects.select_related('user', 'review').get(user=request.user)
    except RiderProfile.DoesNotExist:
        return None, api_response(
            success=False,
            message='Rider profile not found',
            status_code=status.HTTP_404_NOT_FOUND,
        )

    if not rider_profile.is_approved:
        return None, api_response(
            success=False,
            message=(
                'Your profile must be approved by admin before you can manage customers. '
                f'Current status: {rider_profile.review_status}'
            ),
            status_code=status.HTTP_403_FORBIDDEN,
        )

    return rider_profile, None


def get_customer_user_or_none(customer_id):
    """Return customer user with profile, or None if invalid."""
    try:
        customer_id = int(customer_id)
    except (TypeError, ValueError):
        return None

    if customer_id <= 0:
        return None

    from apps.customers.models import CustomerProfile

    try:
        profile = CustomerProfile.objects.select_related('user').get(user_id=customer_id)
    except CustomerProfile.DoesNotExist:
        return None

    customer = profile.user
    if customer is None or customer.is_deleted or not customer.is_active:
        return None

    return customer


def _profile_measurements(profile):
    if not profile or not has_measurement_values(profile.measurements):
        return None
    return public_measurements(profile.measurements)


def _serialize_customer_summary(customer, *, is_existing=True):
    return {
        'id': customer.id,
        'name': customer.get_full_name() or customer.username,
        'phone': customer.phone,
        'email': customer.email,
        'is_existing': is_existing,
        'created_at': customer.date_joined,
    }


def build_rider_customer_payload(customer, request, *, is_existing=True):
    """Build lookup/detail payload with measurements and style presets."""
    profile = customer.customer_profile
    style_presets_map = get_customer_style_presets([customer.id], request=request)
    style_presets = style_presets_map.get(customer.id, [])

    default_preset = UserStylePreset.objects.filter(
        user=customer,
        is_default=True,
    ).order_by('-updated_at', '-id').first()

    return {
        'customer': _serialize_customer_summary(customer, is_existing=is_existing),
        'measurements': _profile_measurements(profile),
        'style_presets': style_presets,
        'default_style_preset_id': default_preset.id if default_preset else None,
    }
