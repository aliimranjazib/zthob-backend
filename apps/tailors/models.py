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
    fabric_image=models.ImageField(upload_to='fabrics/images', validators=image_validator)
    
    def save(self, *args, **kwargs):
        if not self.sku:
            self.sku = f"FAB-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)
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
    order=models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ["order", "id"]
        unique_together = [("fabric", "order")]  # optional: prevent duplicate orders for same fabric

    def __str__(self):
        return f"Gallery image for {self.fabric.name}"
    