from django.db import models
from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils import timezone
from django.core.validators import FileExtensionValidator
from decimal import Decimal

User = get_user_model()

# Image validator for slider images
SLIDER_IMAGE_VALIDATOR = [FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])]

class PhoneVerification(models.Model):
    """Reusable phone verification model for all user types"""
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='phone_verifications'
    )
    phone_number = models.CharField(max_length=20)
    otp_code = models.CharField(max_length=6, blank=True, null=True, help_text="OTP code (for manual OTP) or empty if using Twilio Verify")
    verification_sid = models.CharField(max_length=100, blank=True, null=True, help_text="Twilio Verify verification SID")
    is_verified = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Phone Verification"
        verbose_name_plural = "Phone Verifications"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.phone_number} - {self.otp_code}"
    
    def is_expired(self):
        """Check if OTP has expired"""
        return timezone.now() > self.expires_at
    
    def is_valid(self):
        """Check if OTP is valid and not expired"""
        return not self.is_expired() and not self.is_verified



class BaseModel(models.Model):
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    created_by=models.ForeignKey(User,on_delete=models.SET_NULL,null=True,blank=True,related_name="%(class)s_created")
    

    class Meta:
        abstract=True
        ordering=['-created_at']


class SystemSettings(models.Model):
    """
    System-wide settings managed by admin.
    Singleton pattern - only one instance should exist.
    """
    # Tax/VAT Settings
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal('0.15'),
        help_text="Tax/VAT rate as decimal (e.g., 0.15 for 15%)"
    )
    
    # Delivery Fee Settings
    delivery_fee_under_10km = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('20.00'),
        help_text="Delivery fee for distances less than 10 KM (SAR)"
    )
    
    delivery_fee_10km_and_above = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('30.00'),
        help_text="Delivery fee for distances 10 KM and above (SAR)"
    )
    
    distance_threshold_km = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('10.00'),
        help_text="Distance threshold in KM for different delivery fees"
    )
    
    # Free Delivery Settings
    free_delivery_threshold = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('500.00'),
        help_text="Order subtotal threshold for free delivery (SAR). Set to 0 to disable free delivery."
    )
    
    # Metadata
    is_active = models.BooleanField(
        default=True,
        help_text="Whether these settings are currently active"
    )
    
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Admin notes about these settings"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_settings',
        help_text="Admin who last updated these settings"
    )
    
    class Meta:
        verbose_name = "System Settings"
        verbose_name_plural = "System Settings"
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"System Settings (Tax: {self.tax_rate*100}%, Updated: {self.updated_at.strftime('%Y-%m-%d')})"
    
    @classmethod
    def get_active_settings(cls):
        """Get the active system settings (singleton pattern)"""
        settings_obj = cls.objects.filter(is_active=True).first()
        if not settings_obj:
            # Create default settings if none exist
            settings_obj = cls.objects.create()
        return settings_obj
    
    def save(self, *args, **kwargs):
        """Override save to ensure only one active setting exists"""
        if self.is_active:
            # Deactivate all other settings
            SystemSettings.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)


class Slider(models.Model):
    """
    Slider/Banner model for displaying promotional content on mobile app.
    Admin can manage slider images with text and button text.
    """
    title = models.CharField(
        max_length=200,
        help_text="Title/Heading text to display on the slider"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Description text to display on the slider (optional)"
    )
    image = models.ImageField(
        upload_to='sliders/images/',
        validators=SLIDER_IMAGE_VALIDATOR,
        help_text="Slider image (JPG, JPEG, PNG only)"
    )
    button_text = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Text to display on the button (optional)"
    )
    button_link = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Link/URL to navigate when button is clicked (optional)"
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order (lower numbers appear first)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this slider is currently active and should be displayed"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_sliders',
        help_text="Admin who created this slider"
    )
    
    class Meta:
        verbose_name = "Slider"
        verbose_name_plural = "Sliders"
        ordering = ['order', '-created_at']
    
    def __str__(self):
        return f"{self.title} (Order: {self.order}, Active: {self.is_active})"
