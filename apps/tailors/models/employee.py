# apps/tailors/models/employee.py
from django.db import models
from django.conf import settings


class TailorEmployee(models.Model):
    """
    Links a user to a tailor's shop as an employee.
    A user can only be an employee of ONE shop at a time.
    Roles and permissions are set by the shop owner.
    """

    ROLE_MANAGER     = 'manager'
    ROLE_STITCHER    = 'stitcher'
    ROLE_CUTTER      = 'cutter'
    ROLE_RECEPTIONIST = 'receptionist'
    ROLE_FINISHER    = 'finisher'

    VALID_ROLES = {ROLE_MANAGER, ROLE_STITCHER, ROLE_CUTTER, ROLE_RECEPTIONIST, ROLE_FINISHER}

    tailor = models.ForeignKey(
        'tailors.TailorProfile',
        on_delete=models.CASCADE,
        related_name='employees',
        help_text="The tailor shop this employee belongs to"
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tailor_employee',
        help_text="The user account of this employee"
    )

    # Multiple roles stored as a JSON list e.g. ["stitcher", "cutter"]
    roles = models.JSONField(
        default=list,
        help_text="List of roles assigned to this employee"
    )

    # --- Granular permissions (toggled by the owner) ---
    can_manage_orders    = models.BooleanField(default=False, db_index=True)
    can_manage_catalog   = models.BooleanField(default=False, db_index=True)
    can_view_analytics   = models.BooleanField(default=False, db_index=True)
    can_manage_employees = models.BooleanField(default=False, db_index=True)
    can_manage_pos       = models.BooleanField(default=False, db_index=True)

    is_active = models.BooleanField(default=True, db_index=True)
    joined_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Tailor Employee"
        verbose_name_plural = "Tailor Employees"
        ordering = ['-joined_at']
        indexes = [
            models.Index(fields=['tailor', 'is_active']),
        ]

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.phone} @ {self.tailor}"

    @property
    def permissions_dict(self):
        """Return permissions as a clean dict for API responses."""
        return {
            "can_manage_orders":    self.can_manage_orders,
            "can_manage_catalog":   self.can_manage_catalog,
            "can_view_analytics":   self.can_view_analytics,
            "can_manage_employees": self.can_manage_employees,
            "can_manage_pos":       self.can_manage_pos,
        }
