from collections import defaultdict

from django.db import migrations, models
from django.db.models.functions import Lower


def dedupe_legacy_fabric_names(apps, schema_editor):
    Fabric = apps.get_model('tailors', 'Fabric')
    groups = defaultdict(list)
    for fabric in Fabric.objects.all().order_by('id'):
        key = (fabric.tailor_id, (fabric.name or '').strip().casefold())
        groups[key].append(fabric)

    for fabrics in groups.values():
        if len(fabrics) <= 1:
            continue
        for index, fabric in enumerate(fabrics[1:], start=2):
            base_name = (fabrics[0].name or 'Fabric').strip()[:90]
            fabric.name = f'{base_name} ({index})'[:100]
            fabric.save(update_fields=['name'])


class Migration(migrations.Migration):

    dependencies = [
        ('tailors', '0025_businessownerplussubscription'),
    ]

    operations = [
        migrations.RunPython(dedupe_legacy_fabric_names, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='fabric',
            constraint=models.UniqueConstraint(
                Lower('name'),
                'tailor',
                name='uniq_legacy_fabric_name_per_shop',
            ),
        ),
    ]
