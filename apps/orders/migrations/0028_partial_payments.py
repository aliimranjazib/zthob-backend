# Generated manually for partial-payment checkout support.

import django.db.models.deletion
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


def backfill_payment_summaries(apps, schema_editor):
    Order = apps.get_model('orders', 'Order')
    for order in Order.objects.all().iterator():
        total = order.total_amount or Decimal('0.00')
        if order.payment_status == 'paid':
            order.payment_plan = 'full'
            order.payment_option = order.payment_option or 'full'
            order.paid_amount = total
            order.remaining_amount = Decimal('0.00')
        elif order.payment_method == 'cod' and order.payment_status == 'pending':
            order.payment_plan = 'pay_later'
            order.payment_option = order.payment_option or 'pay_later'
            order.paid_amount = Decimal('0.00')
            order.remaining_amount = total
        else:
            order.payment_plan = order.payment_plan or 'full'
            order.paid_amount = Decimal('0.00')
            order.remaining_amount = total
        order.deposit_amount = Decimal('0.00')
        order.save(update_fields=[
            'payment_plan',
            'payment_option',
            'deposit_amount',
            'paid_amount',
            'remaining_amount',
        ])


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0027_order_payment_reference_checkoutsession'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='payment_status',
            field=models.CharField(choices=[('pending', 'Pending'), ('partially_paid', 'Partially Paid'), ('paid', 'Paid'), ('refunded', 'Refunded')], default='pending', help_text='Payment_status', max_length=20),
        ),
        migrations.AddField(
            model_name='order',
            name='payment_plan',
            field=models.CharField(choices=[('full', 'Full Payment'), ('partial', 'Partial Payment'), ('pay_later', 'Pay Later')], default='full', help_text='Customer selected payment plan', max_length=20),
        ),
        migrations.AddField(
            model_name='order',
            name='payment_option',
            field=models.CharField(blank=True, help_text='Backend-controlled checkout payment option selected by customer', max_length=30, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='deposit_amount',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Advance amount paid at order creation for partial-payment orders', max_digits=10),
        ),
        migrations.AddField(
            model_name='order',
            name='paid_amount',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Total amount collected so far', max_digits=10),
        ),
        migrations.AddField(
            model_name='order',
            name='remaining_amount',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Outstanding balance to collect before handover', max_digits=10),
        ),
        migrations.AddField(
            model_name='checkoutsession',
            name='payment_plan',
            field=models.CharField(blank=True, choices=[('full', 'Full Payment'), ('partial', 'Partial Payment'), ('pay_later', 'Pay Later')], max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='checkoutsession',
            name='payment_option',
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
        migrations.CreateModel(
            name='OrderPayment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('amount', models.DecimalField(decimal_places=2, help_text='Payment amount', max_digits=10)),
                ('payment_method', models.CharField(choices=[('cod', 'Cash on Delivery'), ('credit_card', 'Credit Card'), ('bank_transfer', 'Bank Transfer')], help_text='How this payment was collected', max_length=20)),
                ('payment_type', models.CharField(choices=[('deposit', 'Deposit'), ('remaining_balance', 'Remaining Balance'), ('full_payment', 'Full Payment'), ('refund', 'Refund'), ('adjustment', 'Adjustment')], help_text='Business purpose of this payment', max_length=30)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('paid', 'Paid'), ('failed', 'Failed'), ('refunded', 'Refunded')], db_index=True, default='paid', max_length=20)),
                ('payment_reference', models.CharField(blank=True, help_text='Gateway or manual collection reference', max_length=150, null=True, unique=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('collected_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='collected_order_payments', to=settings.AUTH_USER_MODEL)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_created', to=settings.AUTH_USER_MODEL)),
                ('order', models.ForeignKey(help_text='Order this payment belongs to', on_delete=django.db.models.deletion.CASCADE, related_name='payments', to='orders.order')),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['order', 'status'], name='orders_orde_order_i_596bfb_idx'),
                    models.Index(fields=['payment_method', 'created_at'], name='orders_orde_payment_9e8514_idx'),
                ],
            },
        ),
        migrations.RunPython(backfill_payment_summaries, migrations.RunPython.noop),
    ]
