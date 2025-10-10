
from django.db import models
from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.utils.text import slugify
import uuid

from apps.core.models import BaseModel
IMAGE_VALIDATOR = [FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png"])]

SEASON_CHOICES = [
    ('summer', 'Summer'),
    ('winter', 'Winter'),
    ('all_season', 'All Season'),
]


# =============================================================================
# ABSTRACT BASE CLASSES
# =============================================================================
class SluggedModel(models.Model):
    """Abstract base class with slug field."""
    slug = models.SlugField(max_length=120, unique=True)
    
    class Meta:
        abstract = True
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


# =============================================================================
# PROFILE MODELS
# =============================================================================
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Tailor Profile"
        verbose_name_plural = "Tailor Profiles"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.shop_name or self.user.get_full_name() or self.user.username}"


# =============================================================================
# CATALOG MODELS
# =============================================================================
class FabricType(SluggedModel):
    """Model representing different types of fabrics."""
    
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Name of the fabric type (e.g., Cotton, Silk, Wool)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Fabric Type"
        verbose_name_plural = "Fabric Types"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class FabricCategory(SluggedModel):
    """Model representing fabric categories."""
    
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Name of the fabric category"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this category is active"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Fabric Category"
        verbose_name_plural = "Fabric Categories"
        ordering = ["name"]
    
    def __str__(self):
        return self.name


# =============================================================================
# FABRIC MODELS
# =============================================================================
class Fabric(BaseModel):
    """Model representing a fabric item."""
    
    # Relationships
    tailor = models.ForeignKey(
        TailorProfile,
        on_delete=models.CASCADE,
        related_name="fabrics",
        help_text="Tailor who owns this fabric"
    )
    fabric_type = models.ForeignKey(
        FabricType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fabrics',
        help_text="Type of fabric"
    )
    category = models.ForeignKey(
        FabricCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fabrics",
        help_text="Category of fabric"
    )
    
    # Basic Information
    name = models.CharField(
        max_length=100,
        help_text="Name of the fabric"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Detailed description of the fabric"
    )
    sku = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        help_text="Stock Keeping Unit - auto-generated"
    )
    
    # Pricing and Inventory
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Price per unit"
    )
    stock = models.PositiveIntegerField(
        default=1,
        help_text="Available stock quantity"
    )
    
    # Attributes
    seasons = models.CharField(
        max_length=20,
        choices=SEASON_CHOICES,
        default='all_season',
        help_text='Best suited season for this fabric'
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this fabric is available for sale"
    )
    
    # Legacy field (deprecated)
    fabric_image = models.ImageField(
        upload_to='fabrics/images',
        validators=IMAGE_VALIDATOR,
        null=True,
        blank=True,
        help_text="Legacy single image field - use gallery instead"
    )
    
    class Meta:
        verbose_name = "Fabric"
        verbose_name_plural = "Fabrics"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tailor', 'is_active']),
            models.Index(fields=['fabric_type', 'seasons']),
            models.Index(fields=['category', 'is_active']),
        ]
    
    def save(self, *args, **kwargs):
        """Generate SKU if not provided."""
        if not self.sku:
            self.sku = f"FAB-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)
    
    @property
    def primary_image(self):
        """
        Returns the primary image from the gallery, or the first image in the gallery,
        or the fabric_image field if gallery is empty.
        """
        # Try to get primary image from gallery
        primary_image = self.gallery.filter(is_primary=True).first()
        if primary_image:
            return primary_image.image
        
        # Fall back to first gallery image
        first_gallery_image = self.gallery.first()
        if first_gallery_image:
            return first_gallery_image.image
        
        # Fall back to legacy fabric_image
        return self.fabric_image
    
    @property
    def is_low_stock(self):
        """Check if fabric is low on stock."""
        return self.stock <= 5
    
    @property
    def is_out_of_stock(self):
        """Check if fabric is out of stock."""
        return self.stock == 0
    
    def __str__(self):
        return f"{self.name} ({self.sku})"


class FabricImage(models.Model):
    """Model representing fabric images in a gallery."""
    
    fabric = models.ForeignKey(
        Fabric,
        on_delete=models.CASCADE,
        related_name="gallery",
        help_text="Fabric this image belongs to"
    )
    image = models.ImageField(
        upload_to='fabrics/gallery',
        validators=IMAGE_VALIDATOR,
        help_text="Image file"
    )
    is_primary = models.BooleanField(
        default=False,
        help_text="Designates this image as the primary image"
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order of the image"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Fabric Image"
        verbose_name_plural = "Fabric Images"
        ordering = ["-is_primary", "order", "id"]
        constraints = [
            # Ensure only one primary image per fabric
            models.UniqueConstraint(
                fields=['fabric'],
                condition=models.Q(is_primary=True),
                name='unique_primary_image_per_fabric'
            ),
        ]
        unique_together = [("fabric", "order")]
    
    def save(self, *args, **kwargs):
        """Ensure only one primary image per fabric."""
        if self.is_primary:
            FabricImage.objects.filter(
                fabric=self.fabric,
                is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)
    
    def __str__(self):
        primary_status = " (Primary)" if self.is_primary else ""
        return f"Gallery image for {self.fabric.name}{primary_status}"