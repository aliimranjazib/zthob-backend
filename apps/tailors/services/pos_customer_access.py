"""Access control helpers for tailor POS customer operations."""

from django.contrib.auth import get_user_model

from apps.customers.models import CustomerProfile
from apps.orders.models import Order

User = get_user_model()


def tailor_has_pos_access_to_customer(*, tailor_owner_user, customer_user) -> bool:
    """
    A tailor shop may manage POS data for a customer when:
    - the customer was created via this tailor's POS, or
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
