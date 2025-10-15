# apps/tailors/models/service_areas.py
from django.db import models
from django.conf import settings

class ServiceArea(models.Model):
    """Model representing service areas for delivery calculation."""
    
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

