from collections import defaultdict

from django.db import migrations, models
from django.db.models.functions import Lower


def dedupe_owner_catalog_fabric_names(apps, schema_editor):
    FabricProduct = apps.get_model('fabrics', 'FabricProduct')
    groups = defaultdict(list)
    for product in FabricProduct.objects.filter(show_in_owner_catalog=True).order_by('id'):
        key = (product.business_id, (product.name or '').strip().casefold())
        groups[key].append(product)

    for products in groups.values():
        if len(products) <= 1:
            continue
        for index, product in enumerate(products[1:], start=2):
            base_name = (products[0].name or 'Fabric').strip()[:90]
            product.name = f'{base_name} ({index})'[:100]
            product.save(update_fields=['name'])


class Migration(migrations.Migration):

    dependencies = [
        ('fabrics', '0004_fabricproduct_show_in_owner_catalog'),
    ]

    operations = [
        migrations.RunPython(dedupe_owner_catalog_fabric_names, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='fabricproduct',
            constraint=models.UniqueConstraint(
                Lower('name'),
                'business',
                condition=models.Q(show_in_owner_catalog=True),
                name='uniq_owner_catalog_fabric_name_per_business',
            ),
        ),
    ]
