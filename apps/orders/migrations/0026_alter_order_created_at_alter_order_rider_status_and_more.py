# Historical compatibility migration.
#
# This migration existed on staging but was never committed to git. It is empty
# here because the relevant model changes are already represented by committed
# migrations in the main repo history.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0025_order_express_fee_order_is_express'),
    ]

    operations = []
