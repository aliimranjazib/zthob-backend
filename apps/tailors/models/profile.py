# apps/tailors/models/profile.py
from django.db import models
from django.conf import settings
from django.core.validators import FileExtensionValidator
from decimal import Decimal

class TailorProfile(models.Model):
    """Model representing a tailor's profile information."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_shops',
        help_text="Shop owner who manages this tailor shop",
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tailor_profile',
        null=True,
        blank=True,
        help_text="Legacy primary profile link for backward compatibility",
    )
    shop_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Name of the tailor's shop"
    )
    contact_number = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text="Primary contact number"
    )
    establishment_year = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Year the business was established"
    )
    tailor_experience = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Years of tailoring experience"
    )
    working_hours = models.JSONField(
        default=dict,
        blank=True,
        null=True,
        help_text="Working hours stored as JSON. Format: {'monday': {'is_open': true, 'start_time': '09:00', 'end_time': '18:00'}}"
    )
    address = models.TextField(
        max_length=250,
        blank=True,
        null=True,
        help_text="Business address"
    )
    shop_status = models.BooleanField(
        default=True,
        help_text="Whether the shop is currently open"
    )
    is_pinned = models.BooleanField(
        default=True,
        help_text="Whether this shop appears in the owner quick-access list",
    )
    is_featured = models.BooleanField(
        default=False,
        help_text="Whether this tailor should be featured on the home page"
    )
    is_verified = models.BooleanField(
        default=False,
        help_text="Whether this tailor is verified by the platform"
    )

    # Rating aggregate fields (auto-updated via signals)
    avg_stitching_quality = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00,
        help_text="Average stitching quality rating (cached from TailorRating)"
    )
    avg_on_time_delivery = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00,
        help_text="Average on-time delivery rating (cached from TailorRating)"
    )
    avg_overall_satisfaction = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00,
        help_text="Average overall satisfaction rating (cached from TailorRating)"
    )
    rating_count = models.PositiveIntegerField(
        default=0,
        help_text="Total number of ratings received"
    )
    shop_image = models.ImageField(
        upload_to='tailor_profiles/shop_images/',
        null=True,
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])],
        help_text="Shop image (JPG, JPEG, PNG only)"
    )

    # Express Delivery configuration
    is_express_delivery_enabled = models.BooleanField(
        default=False,
        help_text="Whether this tailor provides express delivery (extra fast stitching)"
    )
    EXPRESS_UNIT_CHOICES = (
        ('hours', 'Hours'),
        ('days', 'Days'),
    )
    express_delivery_unit = models.CharField(
        max_length=10,
        choices=EXPRESS_UNIT_CHOICES,
        default='days',
        help_text="Unit for express_delivery_days value (hours or days)",
    )
    express_delivery_days = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text=(
            "Express duration amount. Interpreted with express_delivery_unit "
            "(e.g. unit=hours and days=6 means 6 hours)."
        ),
    )
    express_delivery_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Extra fee for express delivery"
    )
    is_measurement_fee_enabled = models.BooleanField(
        default=False,
        help_text="Whether this tailor charges a measurement fee"
    )
    measurement_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="One-time fee charged when this tailor sends a rider for measurements"
    )
    standard_stitching_days = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Default standard stitching turnaround in days for this shop",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Tailor Profile"
        verbose_name_plural = "Tailor Profiles"
        ordering = ['-created_at']

    @property
    def shop_owner_user(self):
        """User account that owns this shop for orders and legacy integrations."""
        return self.owner if self.owner_id else self.user

    @property
    def shop_owner_user_id(self):
        owner_user = self.shop_owner_user
        return owner_user.id if owner_user else None
    
    def __str__(self):
        owner_user = self.shop_owner_user
        return f"{self.shop_name or (owner_user.get_full_name() if owner_user else '') or 'Shop'}"
