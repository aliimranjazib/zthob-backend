import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tailors', '0024_shoptailorplussubscription'),
        ('customization', '0007_sync_app_template_pdf_grid'),
    ]

    operations = [
        migrations.CreateModel(
            name='ShopMeasurementSchema',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('base_template', models.ForeignKey(
                    help_text='Platform template this shop customizes',
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='shop_schemas',
                    to='customization.measurementtemplate',
                )),
                ('shop', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='measurement_schema',
                    to='tailors.tailorprofile',
                )),
            ],
            options={
                'verbose_name': 'Shop measurement schema',
                'verbose_name_plural': 'Shop measurement schemas',
            },
        ),
        migrations.CreateModel(
            name='ShopMeasurementField',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(help_text='JSON key stored on orders (must match global name when linked)', max_length=50)),
                ('is_visible', models.BooleanField(default=True, help_text='False removes a platform field from this shop form')),
                ('display_name', models.CharField(blank=True, default='', max_length=100)),
                ('display_name_ar', models.CharField(blank=True, default='', max_length=100)),
                ('display_name_ur', models.CharField(blank=True, default='', max_length=100)),
                ('field_type', models.CharField(
                    choices=[('decimal', 'Decimal Number'), ('integer', 'Whole Number'), ('text', 'Text')],
                    default='decimal',
                    max_length=20,
                )),
                ('min_value', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('max_value', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('is_required', models.BooleanField(default=True)),
                ('display_order', models.PositiveIntegerField(default=0)),
                ('pdf_grid_row', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('pdf_grid_col', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('help_text_en', models.CharField(blank=True, default='', max_length=200)),
                ('help_text_ar', models.CharField(blank=True, default='', max_length=200)),
                ('help_text_ur', models.CharField(blank=True, default='', max_length=200)),
                ('global_field', models.ForeignKey(
                    blank=True,
                    help_text='When set, overrides or hides a platform field',
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='shop_overlays',
                    to='customization.measurementfield',
                )),
                ('schema', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='fields',
                    to='customization.shopmeasurementschema',
                )),
            ],
            options={
                'verbose_name': 'Shop measurement field',
                'verbose_name_plural': 'Shop measurement fields',
                'ordering': ['schema', 'display_order', 'name'],
            },
        ),
        migrations.AddConstraint(
            model_name='shopmeasurementfield',
            constraint=models.UniqueConstraint(fields=('schema', 'name'), name='customization_shopmeasfield_schema_name_uniq'),
        ),
        migrations.AddConstraint(
            model_name='shopmeasurementfield',
            constraint=models.UniqueConstraint(
                condition=models.Q(('global_field__isnull', False)),
                fields=('schema', 'global_field'),
                name='customization_shopmeasfield_schema_global_uniq',
            ),
        ),
    ]
