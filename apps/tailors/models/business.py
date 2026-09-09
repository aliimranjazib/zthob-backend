from django.conf import settings
from django.db import models


class Business(models.Model):
    """Owner-level business entity; parent of shops, staff roster, and fabric catalog."""

    STATUS_DRAFT = 'draft'
    STATUS_ACTIVE = 'active'
    STATUS_SUSPENDED = 'suspended'
    STATUS_CHOICES = (
        (STATUS_DRAFT, 'Draft'),
        (STATUS_ACTIVE, 'Active'),
        (STATUS_SUSPENDED, 'Suspended'),
    )

    SETUP_BUSINESS_CREATED = 'business_created'
    SETUP_FIRST_SHOP_CREATED = 'first_shop_created'
    SETUP_COMPLETED = 'completed'
    SETUP_STEP_CHOICES = (
        (SETUP_BUSINESS_CREATED, 'Business created'),
        (SETUP_FIRST_SHOP_CREATED, 'First shop created'),
        (SETUP_COMPLETED, 'Completed'),
    )

    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='business',
        help_text='Owner account that owns this business',
    )
    name = models.CharField(max_length=150, blank=True, default='')
    contact_phone = models.CharField(max_length=20, blank=True, default='')
    contact_email = models.EmailField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, default='')
    logo = models.ImageField(
        upload_to='business/logos/',
        blank=True,
        null=True,
    )
    default_language = models.CharField(max_length=10, default='ar')
    timezone = models.CharField(max_length=64, default='Asia/Riyadh')
    currency = models.CharField(max_length=3, default='SAR')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
        db_index=True,
    )
    setup_step = models.CharField(
        max_length=32,
        choices=SETUP_STEP_CHOICES,
        default=SETUP_BUSINESS_CREATED,
        db_index=True,
    )
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Business'
        verbose_name_plural = 'Businesses'
        ordering = ['-created_at']

    def __str__(self):
        label = self.name or f'Business #{self.pk}'
        return f'{label} (owner={self.owner_id})'

    @property
    def is_setup_complete(self) -> bool:
        return self.setup_step == self.SETUP_COMPLETED
