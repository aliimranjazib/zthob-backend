# apps/tailors/models/profile.py
from django.db import models
from django.conf import settings
from django.core.validators import FileExtensionValidator

class TailorProfile(models.Model):
    """Model representing a tailor's profile information."""
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tailor_profile'
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
    express_delivery_days = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Number of days for express delivery (e.g. 4 days)"
    )
    express_delivery_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Extra fee for express delivery"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Tailor Profile"
        verbose_name_plural = "Tailor Profiles"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.shop_name or self.user.get_full_name() or self.user.username}"