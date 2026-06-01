# Merge staging's historical checkout merge with the partial-payment migration.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0028_merge_20260526_0858'),
        ('orders', '0028_partial_payments'),
    ]

    operations = []
