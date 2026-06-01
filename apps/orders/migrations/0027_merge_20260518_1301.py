# Historical compatibility merge.
#
# This migration existed on staging before the checkout/partial-payment work was
# committed to git. It is intentionally empty so environments with this applied
# can share the same migration graph as fresh environments.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0026_order_idempotency_key_alter_order_created_at_and_more'),
    ]

    operations = []
