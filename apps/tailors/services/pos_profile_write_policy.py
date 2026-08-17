"""Write-policy rules for POS updates to customer profile data."""

from django.utils import timezone

from apps.customers.services.audit_log import log_customer_data_change
from apps.orders.measurement_utils import has_measurement_values, public_measurements


def _has_profile_measurements(measurements) -> bool:
    return has_measurement_values(measurements)


def can_overwrite_family_member_measurements(
    *,
    family_member,
    replace_profile_measurements=False,
    actor_shop_id=None,
) -> bool:
    if replace_profile_measurements:
        return True
    if not _has_profile_measurements(family_member.measurements):
        return True
    if family_member.customer_edited_at:
        return False
    if family_member.created_source == 'tailor_pos':
        if actor_shop_id and family_member.created_by_shop_id == actor_shop_id:
            return True
        if actor_shop_id is None:
            return True
    return False


def can_overwrite_customer_profile_measurements(
    *,
    customer_profile,
    replace_profile_measurements=False,
) -> bool:
    if replace_profile_measurements:
        return True
    return not _has_profile_measurements(customer_profile.measurements)


def apply_family_member_measurements(
    *,
    family_member,
    measurements_data,
    actor_user=None,
    actor_role='',
    actor_shop_id=None,
    replace_profile_measurements=False,
    source='tailor_pos',
):
    """
    Update family member profile measurements when policy allows.
    Returns (updated: bool, message: str).
    """
    before = family_member.measurements
    if not can_overwrite_family_member_measurements(
        family_member=family_member,
        replace_profile_measurements=replace_profile_measurements,
        actor_shop_id=actor_shop_id,
    ):
        log_customer_data_change(
            customer=family_member.user,
            actor_user=actor_user,
            actor_role=actor_role,
            entity_type='family_member',
            entity_id=family_member.id,
            action='blocked_overwrite',
            before={'measurements': before},
            after={'measurements': measurements_data},
            source=source,
        )
        return False, 'Profile measurements were not updated because customer data is protected.'

    family_member.measurements = public_measurements(measurements_data)
    family_member.last_profile_sync_at = timezone.now()
    family_member.save(update_fields=['measurements', 'last_profile_sync_at'])

    action = 'replace_measurements' if replace_profile_measurements else 'update'
    log_customer_data_change(
        customer=family_member.user,
        actor_user=actor_user,
        actor_role=actor_role,
        entity_type='family_member',
        entity_id=family_member.id,
        action=action,
        before={'measurements': before},
        after={'measurements': measurements_data},
        source=source,
    )
    return True, 'Family member profile measurements updated.'


def apply_customer_profile_measurements(
    *,
    customer_profile,
    measurements_data,
    actor_user=None,
    actor_role='',
    replace_profile_measurements=False,
    source='tailor_pos',
):
    """Update customer profile measurements when policy allows."""
    before = customer_profile.measurements
    if not can_overwrite_customer_profile_measurements(
        customer_profile=customer_profile,
        replace_profile_measurements=replace_profile_measurements,
    ):
        log_customer_data_change(
            customer=customer_profile.user,
            actor_user=actor_user,
            actor_role=actor_role,
            entity_type='customer_profile',
            entity_id=customer_profile.id,
            action='blocked_overwrite',
            before={'measurements': before},
            after={'measurements': measurements_data},
            source=source,
        )
        return False, 'Customer profile measurements were not updated because existing data is protected.'

    customer_profile.measurements = public_measurements(measurements_data)
    customer_profile.save(update_fields=['measurements'])

    action = 'replace_measurements' if replace_profile_measurements else 'update'
    log_customer_data_change(
        customer=customer_profile.user,
        actor_user=actor_user,
        actor_role=actor_role,
        entity_type='customer_profile',
        entity_id=customer_profile.id,
        action=action,
        before={'measurements': before},
        after={'measurements': measurements_data},
        source=source,
    )
    return True, 'Customer profile measurements updated.'


def tailor_can_edit_family_member(*, family_member, actor_shop_id) -> bool:
    """Tailor may edit family member metadata before customer edits it."""
    if family_member.customer_edited_at:
        return False
    if family_member.created_source == 'tailor_pos':
        return (
            family_member.created_by_shop_id is None
            or family_member.created_by_shop_id == actor_shop_id
        )
    return False
