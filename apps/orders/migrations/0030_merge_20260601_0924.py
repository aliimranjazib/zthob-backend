# Merge staging's historical migration branch with the current partial-payment
# branch so Django has a single leaf node.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0027_merge_20260518_1301'),
        ('orders', '0029_merge_20260601_0908'),
    ]

    operations = []
