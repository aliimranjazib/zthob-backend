from django.db import models
from django.conf import settings
from apps.core.models import BaseModel  


class CustomStyleCategory(BaseModel):
    """
    Categories of thobe customization (collar, cuff, pocket, etc.)
    """
    name = models.CharField(
        max_length=50,
        unique=True,
        help_text="Internal name (e.g., 'collar', 'cuff', 'placket')"
    )
    display_name = models.CharField(
        max_length=100,
        help_text="Display name shown to users (e.g., 'Collar Styles', 'Cuff Styles')"
    )
    display_order = models.PositiveIntegerField(
        default=0,
        help_text="Order in which to display categories (lower = first)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this category is available for selection"
    )
    
    class Meta:
        ordering = ['display_order', 'name']  # ← REMOVED EXTRA COMMA
        verbose_name = 'Custom Style Category'
        verbose_name_plural = 'Custom Style Categories'
    
    def __str__(self):
        return self.display_name  # ← CHANGED to display_name (more user-friendly)


class CustomStyle(BaseModel):
    """
    Individual style options within each category
    """
    category = models.ForeignKey(
        CustomStyleCategory,
        on_delete=models.CASCADE,
        related_name='styles',
        help_text="Category this style belongs to"
    )
    name = models.CharField(
        max_length=100,
        help_text="Style name (e.g., 'Standard', 'Mandarin', 'Modern')"
    )
    code = models.CharField(
        max_length=50,
        help_text="Unique code for this style (e.g., 'collar_1_Standard')"
    )
    image = models.ImageField(
        upload_to='custom_styles/%Y/%m/',
        help_text="Style image (PNG/JPG)"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Optional description of this style"
    )
    display_order = models.PositiveIntegerField(  # ← ADDED THIS FIELD
        default=0,
        help_text="Order in which to display within category (lower = first)"
    )
    is_active = models.BooleanField(  # ← ADDED THIS FIELD
        default=True,
        help_text="Whether this style is available for selection"
    )
    extra_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,  # ← Allows NULL in database
        blank=True,  # ← Allows empty in forms
        help_text="Additional cost for this style (leave empty if no extra charge)"
    )
    
    class Meta:
        ordering = ['category', 'display_order', 'name']
        unique_together = ['category', 'code']
        verbose_name = 'Custom Style'
        verbose_name_plural = 'Custom Styles'
    
    def __str__(self):
        return f"{self.category.name} - {self.name}"

class UserStylePreset(BaseModel):
    """
    User's custom style preset
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='style_presets',
        help_text="User this preset belongs to"
    )
    name=models.CharField(
        max_length=100,
        help_text="Name of this style preset"
    )
    description=models.TextField(
        blank=True,
        null=True,
        help_text="Optional description of this style preset"
    )
    styles = models.JSONField(
        default=list,
        help_text="Selected styles. Format: [{'category': 'collar', 'style_id': 8}]"
    )
    is_default = models.BooleanField(
        default=False,
        help_text="Whether this is the user's default style preset"
    )
    usage_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of times this preset has been used"
    )
    class Meta:
        ordering = ['-is_default', '-usage_count', '-created_at']
        verbose_name = 'User Style Preset'
        verbose_name_plural = 'User Style Presets'
        unique_together = ['user', 'name']
    
    def __str__(self):
        return f"{self.user.username} - {self.name}"
    
    def increment_usage(self):
        """Increment usage counter when preset is used"""
        self.usage_count += 1
        self.save(update_fields=['usage_count'])
    
    def set_as_default(self):
        """Set this preset as user's default, unset others"""
        # Unset all other defaults for this user
        UserStylePreset.objects.filter(user=self.user).update(is_default=False)
        # Set this one as default
        self.is_default = True
        self.save(update_fields=['is_default'])


class MeasurementTemplate(BaseModel):
    """
    Admin-defined measurement template (e.g., "Thobe Measurements").
    Defines the structure of measurement forms that tailors/customers fill in.
    """
    UNIT_CHOICES = [
        ('cm', 'Centimeters'),
        ('inches', 'Inches'),
    ]

    name = models.CharField(
        max_length=50,
        unique=True,
        help_text="Internal name (e.g., 'thobe', 'pants')"
    )
    display_name = models.CharField(
        max_length=100,
        help_text="English display name"
    )
    display_name_ar = models.CharField(
        max_length=100,
        help_text="Arabic display name"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Optional description"
    )
    default_unit = models.CharField(
        max_length=10,
        choices=UNIT_CHOICES,
        default='cm',
        help_text="Default unit for measurement fields"
    )
    display_order = models.PositiveIntegerField(
        default=0,
        help_text="Order in which to display templates (lower = first)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this template is available for use"
    )

    class Meta:
        ordering = ['display_order', 'name']
        verbose_name = 'Measurement Template'
        verbose_name_plural = 'Measurement Templates'

    def __str__(self):
        return self.display_name


class MeasurementField(BaseModel):
    """
    Individual measurement field within a template (e.g., "الطول", "الكتف").
    Admin can add, update, delete fields to customize what tailors measure.
    """
    FIELD_TYPE_CHOICES = [
        ('decimal', 'Decimal Number'),
        ('integer', 'Whole Number'),
        ('text', 'Text'),
    ]

    template = models.ForeignKey(
        MeasurementTemplate,
        on_delete=models.CASCADE,
        related_name='fields',
        help_text="Template this field belongs to"
    )
    name = models.CharField(
        max_length=50,
        help_text="Internal key (e.g., 'chest', 'waist')"
    )
    display_name = models.CharField(
        max_length=100,
        help_text="English label"
    )
    display_name_ar = models.CharField(
        max_length=100,
        help_text="Arabic label"
    )
    field_type = models.CharField(
        max_length=20,
        choices=FIELD_TYPE_CHOICES,
        default='decimal',
        help_text="Type of value expected"
    )
    min_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Minimum valid value (for decimal/integer fields)"
    )
    max_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Maximum valid value (for decimal/integer fields)"
    )
    is_required = models.BooleanField(
        default=True,
        help_text="Whether this field must be filled"
    )
    display_order = models.PositiveIntegerField(
        default=0,
        help_text="Order in which to display (lower = first)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this field is shown in the form"
    )
    help_text_en = models.CharField(
        max_length=200,
        blank=True,
        default='',
        help_text="English helper tip for tailor"
    )
    help_text_ar = models.CharField(
        max_length=200,
        blank=True,
        default='',
        help_text="Arabic helper tip for tailor"
    )

    class Meta:
        ordering = ['template', 'display_order', 'name']
        unique_together = ['template', 'name']
        verbose_name = 'Measurement Field'
        verbose_name_plural = 'Measurement Fields'

    def __str__(self):
        return f"{self.template.name} - {self.display_name}"