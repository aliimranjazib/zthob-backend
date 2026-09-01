"""Shared customer lookup/create helpers for POS and rider field flows."""

from dataclasses import dataclass

from django.contrib.auth import get_user_model

from apps.core.phone_format import normalize_phone_to_local, phone_lookup_variations
from apps.customers.models import CustomerProfile
from apps.customers.services.welcome_sms import queue_customer_welcome_sms

User = get_user_model()


@dataclass
class CustomerProvisioningResult:
    user: User
    profile: CustomerProfile
    is_existing: bool
    created: bool


def _split_name(name: str) -> tuple[str, str]:
    name_parts = name.strip().split(' ', 1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else ''
    return first_name, last_name


def _generate_username(phone: str) -> str:
    username = f"user_{phone}"
    counter = 1
    while User.objects.filter(username=username).exists():
        username = f"user_{phone}_{counter}"
        counter += 1
    return username


def _apply_name_to_user(user: User, name: str) -> None:
    first_name, last_name = _split_name(name)
    user.first_name = first_name
    user.last_name = last_name
    user.save(update_fields=['first_name', 'last_name'])


def lookup_or_create_customer(
    *,
    phone: str,
    name: str,
    pos_created_by=None,
    send_welcome_sms: bool = True,
) -> CustomerProvisioningResult:
    """
    Find a customer by phone or create User + CustomerProfile.

    ``phone`` must already be normalized to local format.
    """
    existing_user = User.objects.filter(phone__in=phone_lookup_variations(phone)).first()

    if existing_user:
        if existing_user.phone != phone:
            existing_user.phone = phone
            existing_user.save(update_fields=['phone'])
        _apply_name_to_user(existing_user, name)

        profile_defaults = {}
        if pos_created_by is not None:
            profile_defaults['pos_created_by'] = pos_created_by

        try:
            profile = existing_user.customer_profile
            if pos_created_by is not None and not profile.pos_created_by_id:
                profile.pos_created_by = pos_created_by
                profile.save(update_fields=['pos_created_by'])
        except CustomerProfile.DoesNotExist:
            profile = CustomerProfile.objects.create(
                user=existing_user,
                **profile_defaults,
            )

        return CustomerProvisioningResult(
            user=existing_user,
            profile=profile,
            is_existing=True,
            created=False,
        )

    first_name, last_name = _split_name(name)
    user = User.objects.create(
        username=_generate_username(phone),
        phone=phone,
        first_name=first_name,
        last_name=last_name,
        role='USER',
        is_active=True,
    )

    profile_kwargs = {}
    if pos_created_by is not None:
        profile_kwargs['pos_created_by'] = pos_created_by

    profile = CustomerProfile.objects.create(user=user, **profile_kwargs)

    if send_welcome_sms:
        queue_customer_welcome_sms(user.id)

    return CustomerProvisioningResult(
        user=user,
        profile=profile,
        is_existing=False,
        created=True,
    )


def normalize_customer_phone(phone: str) -> str:
    """Normalize raw phone input to canonical local format."""
    return normalize_phone_to_local(phone)
