# Merge staging's historical 0026 branch with the current orders migration leaf.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0026_alter_order_created_at_alter_order_rider_status_and_more'),
        ('orders', '0030_merge_20260601_0924'),
    ]

    operations = []
