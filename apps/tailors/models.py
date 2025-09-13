from django.db import models
from django.conf import settings
import uuid
from django.core.validators import FileExtensionValidator

from apps.core.models import BaseModel
# Create your models here.
class TailorProfile(models.Model):
    user=models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,
                            related_name='tailor_profile')
    shop_name=models.CharField(max_length=100,blank=True,null=True)
    contact_number=models.CharField(max_length=20,null=True,blank=True)
    establishment_year=models.PositiveIntegerField(blank=True, null=True, default=None)
    tailor_experience=models.PositiveIntegerField(blank=True, null=True, default=None)
    working_hours=models.JSONField(default=dict,blank=True,null=True,   
                                help_text="Working hours stored as JSON. Format: {'monday': {'is_open': true, 'start_time': '09:00', 'end_time': '18:00'}}")
    address = models.TextField(max_length=250, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    shop_status=models.BooleanField(default=True)
    

class FabricCategory(models.Model):
    name=models.CharField(max_length=100, unique=True)
    slug=models.SlugField(max_length=120, unique=True)
    is_active=models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
    
image_validator=[FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png"])]

class Fabric(BaseModel):
    tailor=models.ForeignKey(TailorProfile,
                             on_delete=models.CASCADE,
                             related_name="fabrics",)
    category=models.ForeignKey(FabricCategory,
                                on_delete=models.SET_NULL,
                                null=True,
                                blank=True,
                                related_name="fabrics"
                               )
    name=models.CharField(max_length=100)
    description=models.TextField(blank=True, null=True)
    sku=models.CharField(max_length=20,unique=True,editable=False)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    # Keep this for backward compatibility but it will be deprecated
    fabric_image=models.ImageField(upload_to='fabrics/images', validators=image_validator, null=True, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.sku:
            self.sku = f"FAB-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)
    
    @property
    def primary_image(self):
        """
        Returns the primary image from the gallery, or the first image in the gallery,
        or the fabric_image field if gallery is empty
        """
        primary_image = self.gallery.filter(is_primary=True).first()
        if primary_image:
            return primary_image.image
        
        # Fall back to first gallery image
        first_gallery_image = self.gallery.first()
        if first_gallery_image:
            return first_gallery_image.image
        
        # Fall back to fabric_image
        return self.fabric_image
    
    def __str__(self):
        return f"{self.name} ({self.sku})"
    
    
class FabricImage(models.Model):
    fabric=models.ForeignKey(Fabric,
                             on_delete=models.CASCADE,
                             related_name="gallery"
                             )
    image=models.ImageField(
        upload_to='fabrics/gallery',
        validators=image_validator
    )
    is_primary = models.BooleanField(default=False, help_text="Designates this image as the primary image")
    order=models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ["-is_primary", "order", "id"]
        constraints = [
            # Ensure only one primary image per fabric
            models.UniqueConstraint(
                fields=['fabric'],
                condition=models.Q(is_primary=True),
                name='unique_primary_image'
            ),
        ]
        unique_together = [("fabric", "order")]  # prevent duplicate orders for same fabric

    def save(self, *args, **kwargs):
        # If this is being set as primary, unset any existing primary
        if self.is_primary:
            FabricImage.objects.filter(fabric=self.fabric, is_primary=True).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)

    def __str__(self):
        primary_status = " (Primary)" if self.is_primary else ""
        return f"Gallery image for {self.fabric.name}{primary_status}"
    