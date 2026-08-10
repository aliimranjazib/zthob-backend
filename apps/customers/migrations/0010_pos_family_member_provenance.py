from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tailors', '0016_tailorprofile_standard_stitching_days'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('customers', '0009_customerprofile_welcome_sms_sent_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='familymember',
            name='created_source',
            field=models.CharField(
                choices=[('customer_app', 'Customer App'), ('tailor_pos', 'Tailor POS')],
                db_index=True,
                default='customer_app',
                help_text='Where this family member record was created',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='familymember',
            name='created_by_tailor',
            field=models.ForeignKey(
                blank=True,
                help_text='Tailor shop owner who created this family member via POS',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='pos_created_family_members',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='familymember',
            name='created_by_shop',
            field=models.ForeignKey(
                blank=True,
                help_text='Tailor shop profile that created this family member via POS',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='pos_created_family_members',
                to='tailors.tailorprofile',
            ),
        ),
        migrations.AddField(
            model_name='familymember',
            name='customer_edited_at',
            field=models.DateTimeField(
                blank=True,
                help_text='When the customer last edited this family member in the customer app',
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='familymember',
            name='last_profile_sync_at',
            field=models.DateTimeField(
                blank=True,
                help_text='When profile measurements were last synced from POS/order flows',
                null=True,
            ),
        ),
        migrations.CreateModel(
            name='CustomerDataAuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('actor_role', models.CharField(blank=True, default='', max_length=20)),
                ('entity_type', models.CharField(choices=[('family_member', 'Family Member'), ('customer_profile', 'Customer Profile')], max_length=30)),
                ('entity_id', models.PositiveIntegerField(blank=True, null=True)),
                ('action', models.CharField(choices=[('create', 'Create'), ('update', 'Update'), ('delete', 'Delete'), ('blocked_overwrite', 'Blocked Overwrite'), ('replace_measurements', 'Replace Measurements')], max_length=30)),
                ('before', models.JSONField(blank=True, null=True)),
                ('after', models.JSONField(blank=True, null=True)),
                ('source', models.CharField(choices=[('customer_app', 'Customer App'), ('tailor_pos', 'Tailor POS'), ('system', 'System')], default='system', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('actor_user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='customer_data_audit_actions', to=settings.AUTH_USER_MODEL)),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='data_audit_logs', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['customer', 'created_at'], name='customers_c_custome_0a8f0d_idx'),
                    models.Index(fields=['entity_type', 'entity_id'], name='customers_c_entity__b8e0f1_idx'),
                ],
            },
        ),
    ]
