"""Customer data audit logging helpers."""

from apps.customers.models import CustomerDataAuditLog


def log_customer_data_change(
    *,
    customer,
    actor_user=None,
    actor_role='',
    entity_type,
    entity_id=None,
    action,
    before=None,
    after=None,
    source='system',
):
    return CustomerDataAuditLog.objects.create(
        customer=customer,
        actor_user=actor_user,
        actor_role=actor_role or '',
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        before=before,
        after=after,
        source=source,
    )
