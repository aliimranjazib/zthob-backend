"""Access control helpers for tailor POS customer operations."""

from django.contrib.auth import get_user_model

from apps.customers.models import CustomerProfile, TailorPOSCustomerLink
from apps.orders.models import Order

User = get_user_model()


def ensure_pos_customer_link(*, tailor_owner_user, customer_user):
    """Attach this shop owner to the customer for POS without changing pos_created_by."""
    if not tailor_owner_user or not customer_user:
        return None

    link, _created = TailorPOSCustomerLink.objects.get_or_create(
        customer=customer_user,
        tailor=tailor_owner_user,
    )
    return link


def tailor_has_pos_access_to_customer(*, tailor_owner_user, customer_user) -> bool:
    """
    A tailor shop may manage POS data for a customer when:
    - the customer was created via this tailor's POS, or
    - this tailor added the customer in POS (shop link), or
    - the customer has at least one order with this tailor.
    """
    if not tailor_owner_user or not customer_user:
        return False

    try:
        profile = customer_user.customer_profile
        if profile.pos_created_by_id == tailor_owner_user.id:
            return True
    except CustomerProfile.DoesNotExist:
        pass

    if TailorPOSCustomerLink.objects.filter(
        customer=customer_user,
        tailor=tailor_owner_user,
    ).exists():
        return True

    return Order.objects.filter(
        customer=customer_user,
        tailor=tailor_owner_user,
    ).exists()


def get_customer_for_pos_or_none(*, tailor_owner_user, customer_id):
    """Return customer user if tailor has POS access, else None."""
    try:
        customer = User.objects.get(id=customer_id)
    except User.DoesNotExist:
        return None

    if not tailor_has_pos_access_to_customer(
        tailor_owner_user=tailor_owner_user,
        customer_user=customer,
    ):
        return None
    return customer


def pos_owned_by_tailor(*, tailor_owner_user, profile) -> bool:
    """True when this shop owner originally created the customer in POS."""
    return bool(
        tailor_owner_user
        and profile
        and profile.pos_created_by_id == tailor_owner_user.id
    )
