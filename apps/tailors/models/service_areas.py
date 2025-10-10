# apps/tailors/models/service_areas.py
from django.db import models
from django.conf import settings

class ServiceArea(models.Model):
    """Model representing service areas that tailors can serve."""
    
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Name of the service area (e.g., Riyadh, Jeddah, Dammam)"
    )
    city = models.CharField(
        max_length=100,
        help_text="City this service area belongs to"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this service area is available for selection"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Service Area"
        verbose_name_plural = "Service Areas"
        ordering = ['city', 'name']
        indexes = [
            models.Index(fields=['city', 'is_active']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.name}, {self.city}"

class TailorServiceArea(models.Model):
    """Model representing which service areas a tailor serves."""
    
    tailor = models.ForeignKey(
        'TailorProfile',
        on_delete=models.CASCADE,
        related_name='service_areas',
        help_text="Tailor who serves this area"
    )
    service_area = models.ForeignKey(
        ServiceArea,
        on_delete=models.CASCADE,
        related_name='tailors',
        help_text="Service area being served"
    )
    is_primary = models.BooleanField(
        default=False,
        help_text="Whether this is the tailor's primary service area"
    )
    delivery_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Delivery fee for this area (optional)"
    )
    estimated_delivery_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Estimated delivery time in days (optional)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Tailor Service Area"
        verbose_name_plural = "Tailor Service Areas"
        unique_together = [('tailor', 'service_area')]
        ordering = ['-is_primary', 'service_area__city', 'service_area__name']
    
    def __str__(self):
        primary_status = " (Primary)" if self.is_primary else ""
        return f"{self.tailor.shop_name} serves {self.service_area.name}{primary_status}"
    
    def save(self, *args, **kwargs):
        """Ensure only one primary service area per tailor."""
        if self.is_primary:
            # Unset other primary areas for this tailor
            TailorServiceArea.objects.filter(
                tailor=self.tailor,
                is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)
