# Generated manually for TaxInvoice model

import decimal
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('orders', '0043_order_shop'),
        ('tailors', '0025_businessownerplussubscription'),
    ]

    operations = [
        migrations.CreateModel(
            name='TaxInvoice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('external_id', models.CharField(db_index=True, max_length=64, unique=True)),
                ('provider', models.CharField(default='zatca_tools', max_length=32)),
                ('invoice_type', models.CharField(default='simplified', max_length=32)),
                ('provider_number', models.CharField(blank=True, default='', max_length=64)),
                ('uuid', models.UUIDField(blank=True, null=True)),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Pending'),
                        ('submitting', 'Submitting'),
                        ('accepted', 'Accepted'),
                        ('warnings', 'Accepted with warnings'),
                        ('rejected', 'Rejected by ZATCA'),
                        ('failed', 'Failed to submit'),
                    ],
                    db_index=True,
                    default='pending',
                    max_length=20,
                )),
                ('zatca_channel', models.CharField(blank=True, default='', max_length=32)),
                ('zatca_icv', models.PositiveIntegerField(blank=True, null=True)),
                ('taxable_amount', models.DecimalField(decimal_places=2, default=decimal.Decimal('0.00'), max_digits=12)),
                ('vat_amount', models.DecimalField(decimal_places=2, default=decimal.Decimal('0.00'), max_digits=12)),
                ('grand_total', models.DecimalField(decimal_places=2, default=decimal.Decimal('0.00'), max_digits=12)),
                ('view_url', models.URLField(blank=True, default='', max_length=500)),
                ('pdf_file', models.FileField(blank=True, null=True, upload_to='tax_invoices/pdf/')),
                ('xml_file', models.FileField(blank=True, null=True, upload_to='tax_invoices/xml/')),
                ('raw_response', models.JSONField(blank=True, default=dict)),
                ('error_code', models.CharField(blank=True, default='', max_length=64)),
                ('error_message', models.TextField(blank=True, default='')),
                ('issued_at', models.DateTimeField(blank=True, null=True)),
                ('order', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='tax_invoice', to='orders.order')),
                ('shop', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tax_invoices', to='tailors.tailorprofile')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
