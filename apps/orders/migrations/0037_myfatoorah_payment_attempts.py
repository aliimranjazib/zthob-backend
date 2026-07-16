import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0036_order_measurement_fee'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='MyFatoorahWebhookEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('event_reference', models.CharField(db_index=True, max_length=100, unique=True)),
                ('event_name', models.CharField(max_length=100)),
                ('invoice_id', models.CharField(blank=True, db_index=True, max_length=100, null=True)),
                ('payment_id', models.CharField(blank=True, db_index=True, max_length=150, null=True)),
                ('transaction_status', models.CharField(blank=True, max_length=50, null=True)),
                ('attempts', models.PositiveIntegerField(default=0)),
                ('processed_at', models.DateTimeField(blank=True, null=True)),
                ('last_error', models.CharField(blank=True, max_length=255, null=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_created', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='CheckoutPaymentAttempt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('attempt_reference', models.CharField(db_index=True, max_length=40, unique=True)),
                ('purpose', models.CharField(choices=[('checkout', 'Checkout'), ('remaining_balance', 'Remaining Balance')], max_length=30)),
                ('provider', models.CharField(default='myfatoorah', max_length=30)),
                ('payment_option', models.CharField(max_length=30)),
                ('expected_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('currency', models.CharField(default='SAR', max_length=3)),
                ('status', models.CharField(choices=[('prepared', 'Prepared'), ('invoice_created', 'Invoice Created'), ('pending', 'Pending'), ('succeeded', 'Succeeded'), ('requires_review', 'Requires Review'), ('failed', 'Failed'), ('expired', 'Expired')], db_index=True, default='prepared', max_length=20)),
                ('client_idempotency_key', models.CharField(blank=True, max_length=100, null=True)),
                ('invoice_id', models.CharField(blank=True, max_length=100, null=True, unique=True)),
                ('payment_id', models.CharField(blank=True, max_length=150, null=True, unique=True)),
                ('gateway_status', models.CharField(blank=True, max_length=50, null=True)),
                ('gateway_payment_method', models.CharField(blank=True, max_length=100, null=True)),
                ('verified_at', models.DateTimeField(blank=True, null=True)),
                ('failure_reason', models.CharField(blank=True, max_length=255, null=True)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('expires_at', models.DateTimeField(db_index=True)),
                ('checkout', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='payment_attempts', to='orders.checkoutsession')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_created', to=settings.AUTH_USER_MODEL)),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='checkout_payment_attempts', to=settings.AUTH_USER_MODEL)),
                ('remaining_session', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='payment_attempts', to='orders.remainingpaymentsession')),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['customer', 'status'], name='orders_chec_custome_e0f9ed_idx'),
                    models.Index(fields=['checkout', 'status'], name='orders_chec_checkou_14138f_idx'),
                    models.Index(fields=['remaining_session', 'status'], name='orders_chec_remaini_73b73e_idx'),
                ],
                'constraints': [
                    models.CheckConstraint(condition=(Q(('checkout__isnull', False), ('remaining_session__isnull', True)) | Q(('checkout__isnull', True), ('remaining_session__isnull', False))), name='payment_attempt_has_one_parent'),
                    models.UniqueConstraint(condition=Q(('client_idempotency_key__isnull', False)), fields=('customer', 'client_idempotency_key'), name='unique_customer_payment_attempt_idempotency'),
                ],
            },
        ),
    ]
