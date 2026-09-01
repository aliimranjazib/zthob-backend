from django.db import models
from django.conf import settings

# Create your models here.

class Address(models.Model):
    ADDRESS_TAG_CHOICES = [
        ('home', 'Home'),
        ('office', 'Office'),
        ('work', 'Work'),
        ('other', 'Other'),
    ]
    
    user=models.ForeignKey(settings.AUTH_USER_MODEL,
                            on_delete=models.CASCADE, 
                            related_name="addresses", 
                            null=True, blank=True)
    street = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state_province = models.CharField(max_length=100, blank=True, null=True)
    zip_code = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=100, default="Saudi Arabia")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    is_default = models.BooleanField(default=False)
    address = models.TextField(blank=True, null=True, help_text="Full address text")
    address_tag = models.CharField(max_length=20, choices=ADDRESS_TAG_CHOICES, default='home', help_text="Address type: home, office, work, other")
    extra_info = models.TextField(blank=True, null=True, help_text="Additional address information")
    class Meta:
        verbose_name_plural = "Addresses"

    

    def __str__(self):
        return f"{self.street}, {self.city}"
    
    def save(self, *args, **kwargs):
        if self.is_default and self.user:  # Added check for self.user
        # unset other defaults for this user
            Address.objects.filter(user=self.user, is_default=True).update(is_default=False)
        
        super().save(*args, **kwargs)



class CustomerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                null=True, blank=True,
                                related_name='customer_profile')
    gender=models.CharField(max_length=10, blank=True,null=True)
    date_of_birth=models.DateField(blank=True,null=True)
    measurements = models.JSONField(blank=True, null=True)
    default_address=models.ForeignKey(Address, on_delete=models.SET_NULL,
                                    null=True,
                                    blank=True,
                                    related_name="default_for_customers")
    loyalty_points = models.IntegerField(null=True, blank=True)
    tags=models.CharField(max_length=20, blank=True, null=True)
    
    # Free measurement service tracking (account-level, one-time)
    first_free_measurement_used = models.BooleanField(
        default=False,
        help_text="Whether customer account has used the one-time free measurement service"
    )
    free_measurement_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the free measurement order was completed"
    )

    # POS tracking: which tailor created this customer via the POS system
    pos_created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pos_created_customers',
        help_text="Tailor who created this customer via the POS system"
    )
    welcome_sms_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the onboarding welcome SMS was sent to this customer",
    )

    def __str__(self):
        return f"Customer Profile for {self.user.username}"
    
class FamilyMember(models.Model):
    CREATED_SOURCE_CHOICES = (
        ('customer_app', 'Customer App'),
        ('tailor_pos', 'Tailor POS'),
    )

    user=models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                            related_name="family_profile")
    name = models.CharField(max_length=255)
    gender = models.CharField(max_length=10, blank=True, null=True)
    relationship = models.CharField(max_length=50, blank=True, null=True)
    measurements = models.JSONField(blank=True, null=True)
    address=models.ForeignKey(Address, on_delete=models.CASCADE, null=True,blank=True)
    created_source = models.CharField(
        max_length=20,
        choices=CREATED_SOURCE_CHOICES,
        default='customer_app',
        db_index=True,
        help_text="Where this family member record was created",
    )
    created_by_tailor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pos_created_family_members',
        help_text='Tailor shop owner who created this family member via POS',
    )
    created_by_shop = models.ForeignKey(
        'tailors.TailorProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pos_created_family_members',
        help_text='Tailor shop profile that created this family member via POS',
    )
    customer_edited_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the customer last edited this family member in the customer app',
    )
    last_profile_sync_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When profile measurements were last synced from POS/order flows',
    )
    
    def __str__(self):
        return f"{self.name} ({self.relationship}) for {self.user.username}"


class CustomerDataAuditLog(models.Model):
    """Audit trail for customer profile changes initiated by POS or customer."""

    ENTITY_TYPE_CHOICES = (
        ('family_member', 'Family Member'),
        ('customer_profile', 'Customer Profile'),
    )
    ACTION_CHOICES = (
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('blocked_overwrite', 'Blocked Overwrite'),
        ('replace_measurements', 'Replace Measurements'),
    )
    SOURCE_CHOICES = (
        ('customer_app', 'Customer App'),
        ('tailor_pos', 'Tailor POS'),
        ('rider_app', 'Rider App'),
        ('system', 'System'),
    )

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='data_audit_logs',
    )
    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='customer_data_audit_actions',
    )
    actor_role = models.CharField(max_length=20, blank=True, default='')
    entity_type = models.CharField(max_length=30, choices=ENTITY_TYPE_CHOICES)
    entity_id = models.PositiveIntegerField(null=True, blank=True)
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    before = models.JSONField(null=True, blank=True)
    after = models.JSONField(null=True, blank=True)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='system')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer', 'created_at']),
            models.Index(fields=['entity_type', 'entity_id']),
        ]

    def __str__(self):
        return f"{self.action} {self.entity_type}:{self.entity_id} for customer {self.customer_id}"


class FabricFavorite(models.Model):
    """Model representing a user's favorite fabric."""
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="fabric_favorites",
        help_text="User who favorited this fabric"
    )
    fabric = models.ForeignKey(
        'tailors.Fabric',
        on_delete=models.CASCADE,
        related_name="favorites",
        help_text="Fabric that was favorited"
    )
    created_at = models.DateTimeField(auto_now_add=True, help_text="When the fabric was favorited")
    
    class Meta:
        verbose_name = "Fabric Favorite"
        verbose_name_plural = "Fabric Favorites"
        ordering = ['-created_at']
        unique_together = [('user', 'fabric')]
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['fabric', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} favorited {self.fabric.name}"