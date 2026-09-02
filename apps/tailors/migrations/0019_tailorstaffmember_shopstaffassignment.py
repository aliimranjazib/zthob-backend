from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def forwards_backfill_staff_from_employees(apps, schema_editor):
    TailorEmployee = apps.get_model('tailors', 'TailorEmployee')
    TailorStaffMember = apps.get_model('tailors', 'TailorStaffMember')
    ShopStaffAssignment = apps.get_model('tailors', 'ShopStaffAssignment')

    for employee in TailorEmployee.objects.select_related('tailor', 'user').iterator():
        owner_id = employee.tailor.owner_id or employee.tailor.user_id
        if not owner_id:
            continue

        staff_member, _created = TailorStaffMember.objects.get_or_create(
            owner_id=owner_id,
            user_id=employee.user_id,
            defaults={'is_active': employee.is_active},
        )
        if not staff_member.is_active and employee.is_active:
            staff_member.is_active = True
            staff_member.save(update_fields=['is_active'])

        assignment, created = ShopStaffAssignment.objects.get_or_create(
            staff_member=staff_member,
            shop_id=employee.tailor_id,
            defaults={
                'roles': employee.roles or [],
                'can_manage_orders': employee.can_manage_orders,
                'can_manage_catalog': employee.can_manage_catalog,
                'can_view_analytics': employee.can_view_analytics,
                'can_manage_employees': employee.can_manage_employees,
                'can_manage_pos': employee.can_manage_pos,
                'can_manage_shop_profile': employee.can_manage_shop_profile,
                'can_manage_shop_status': employee.can_manage_shop_status,
                'can_manage_shop_address': employee.can_manage_shop_address,
                'can_stitch_orders': employee.can_stitch_orders,
                'is_active': employee.is_active,
            },
        )
        if not created:
            continue


class Migration(migrations.Migration):

    dependencies = [
        ('tailors', '0018_tailorprofile_owner_and_is_pinned'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='TailorStaffMember',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('joined_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('owner', models.ForeignKey(help_text='Shop owner who manages this staff member', on_delete=django.db.models.deletion.CASCADE, related_name='staff_roster', to=settings.AUTH_USER_MODEL)),
                ('user', models.ForeignKey(help_text='Staff user account', on_delete=django.db.models.deletion.CASCADE, related_name='owner_staff_memberships', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Tailor Staff Member',
                'verbose_name_plural': 'Tailor Staff Members',
                'ordering': ['-joined_at'],
            },
        ),
        migrations.CreateModel(
            name='ShopStaffAssignment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('roles', models.JSONField(default=list)),
                ('can_manage_orders', models.BooleanField(db_index=True, default=False)),
                ('can_manage_catalog', models.BooleanField(db_index=True, default=False)),
                ('can_view_analytics', models.BooleanField(db_index=True, default=False)),
                ('can_manage_employees', models.BooleanField(db_index=True, default=False)),
                ('can_manage_pos', models.BooleanField(db_index=True, default=False)),
                ('can_manage_shop_profile', models.BooleanField(db_index=True, default=False)),
                ('can_manage_shop_status', models.BooleanField(db_index=True, default=False)),
                ('can_manage_shop_address', models.BooleanField(db_index=True, default=False)),
                ('can_stitch_orders', models.BooleanField(db_index=True, default=False)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('assigned_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('shop', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='staff_assignments', to='tailors.tailorprofile')),
                ('staff_member', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='shop_assignments', to='tailors.tailorstaffmember')),
            ],
            options={
                'verbose_name': 'Shop Staff Assignment',
                'verbose_name_plural': 'Shop Staff Assignments',
                'ordering': ['-assigned_at'],
            },
        ),
        migrations.AddIndex(
            model_name='shopstaffassignment',
            index=models.Index(fields=['shop', 'is_active'], name='tailors_sho_shop_id_6f8b0d_idx'),
        ),
        migrations.AddConstraint(
            model_name='tailorstaffmember',
            constraint=models.UniqueConstraint(fields=('owner', 'user'), name='uniq_staff_member_per_owner_user'),
        ),
        migrations.AddConstraint(
            model_name='shopstaffassignment',
            constraint=models.UniqueConstraint(fields=('staff_member', 'shop'), name='uniq_staff_assignment_per_shop'),
        ),
        migrations.RunPython(forwards_backfill_staff_from_employees, migrations.RunPython.noop),
    ]
