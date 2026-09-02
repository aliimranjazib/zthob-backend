from django.conf import settings
from django.db import models

from apps.tailors.models.employee import TailorEmployee

STAFF_PERMISSION_KEYS = [
    'can_manage_orders',
    'can_manage_catalog',
    'can_view_analytics',
    'can_manage_employees',
    'can_manage_pos',
    'can_manage_shop_profile',
    'can_manage_shop_status',
    'can_manage_shop_address',
    'can_stitch_orders',
]


class TailorStaffMember(models.Model):
    """Owner-scoped staff roster entry (one person may work at multiple shops)."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='staff_roster',
        help_text='Shop owner who manages this staff member',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owner_staff_memberships',
        help_text='Staff user account',
    )
    is_active = models.BooleanField(default=True, db_index=True)
    joined_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Tailor Staff Member'
        verbose_name_plural = 'Tailor Staff Members'
        ordering = ['-joined_at']
        constraints = [
            models.UniqueConstraint(
                fields=['owner', 'user'],
                name='uniq_staff_member_per_owner_user',
            ),
        ]

    def __str__(self):
        label = self.user.get_full_name() or self.user.phone or self.user_id
        return f'{label} @ owner {self.owner_id}'


class ShopStaffAssignment(models.Model):
    """Per-shop roles and permissions for a roster member."""

    staff_member = models.ForeignKey(
        TailorStaffMember,
        on_delete=models.CASCADE,
        related_name='shop_assignments',
    )
    shop = models.ForeignKey(
        'tailors.TailorProfile',
        on_delete=models.CASCADE,
        related_name='staff_assignments',
    )
    roles = models.JSONField(default=list)
    can_manage_orders = models.BooleanField(default=False, db_index=True)
    can_manage_catalog = models.BooleanField(default=False, db_index=True)
    can_view_analytics = models.BooleanField(default=False, db_index=True)
    can_manage_employees = models.BooleanField(default=False, db_index=True)
    can_manage_pos = models.BooleanField(default=False, db_index=True)
    can_manage_shop_profile = models.BooleanField(default=False, db_index=True)
    can_manage_shop_status = models.BooleanField(default=False, db_index=True)
    can_manage_shop_address = models.BooleanField(default=False, db_index=True)
    can_stitch_orders = models.BooleanField(default=False, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    assigned_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Shop Staff Assignment'
        verbose_name_plural = 'Shop Staff Assignments'
        ordering = ['-assigned_at']
        constraints = [
            models.UniqueConstraint(
                fields=['staff_member', 'shop'],
                name='uniq_staff_assignment_per_shop',
            ),
        ]
        indexes = [
            models.Index(fields=['shop', 'is_active']),
        ]

    def __str__(self):
        return f'{self.staff_member_id} -> shop {self.shop_id}'

    @property
    def tailor(self):
        return self.shop

    @property
    def tailor_id(self):
        return self.shop_id

    @property
    def user(self):
        return self.staff_member.user

    @property
    def permissions_dict(self):
        return {
            'can_manage_orders': self.can_manage_orders,
            'can_manage_catalog': self.can_manage_catalog,
            'can_view_analytics': self.can_view_analytics,
            'can_manage_employees': self.can_manage_employees,
            'can_manage_pos': self.can_manage_pos,
            'can_manage_shop_profile': self.can_manage_shop_profile,
            'can_manage_shop_status': self.can_manage_shop_status,
            'can_manage_shop_address': self.can_manage_shop_address,
            'can_stitch_orders': self.can_stitch_orders,
        }

    def apply_roles_and_permissions(self, roles, permissions):
        unknown_roles = set(roles or []) - TailorEmployee.VALID_ROLES
        if unknown_roles:
            raise ValueError(f'Invalid roles: {", ".join(sorted(unknown_roles))}')

        valid_permissions = set(STAFF_PERMISSION_KEYS)
        unknown_permissions = set(permissions or []) - valid_permissions
        if unknown_permissions:
            raise ValueError(
                f'Invalid permissions: {", ".join(sorted(unknown_permissions))}'
            )

        self.roles = list(set(roles or []))
        for key in STAFF_PERMISSION_KEYS:
            setattr(self, key, key in (permissions or []))
