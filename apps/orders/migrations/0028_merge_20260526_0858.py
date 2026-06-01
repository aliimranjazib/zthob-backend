# Historical compatibility merge.
#
# This migration was created/applied on staging to resolve the earlier checkout
# migration branch. Keeping the same name in git lets all environments share one
# migration graph instead of staging carrying an untracked local migration.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0027_order_payment_reference_checkoutsession'),
    ]

    operations = []
