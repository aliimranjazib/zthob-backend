"""
Measurement Models

Defines measurement templates and fields for dynamic measurement configuration.
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError


class MeasurementTemplate(models.Model):
    """
    Measurement template (e.g., "Standard Thobe", "Kids Thobe")
    Contains multiple measurement fields configured by admin.
    """
    GARMENT_TYPES = [
        ('thobe', 'Thobe'),
        ('bisht', 'Bisht'),
        ('jacket', 'Jacket'),
        ('pants', 'Pants'),
        ('shirt', 'Shirt'),
        ('other', 'Other'),
    ]
    
    name_en = models.CharField(
        max_length=100,
        verbose_name='Template Name (English)',
        help_text='e.g., "Standard Thobe", "Premium Bisht"'
    )
    name_ar = models.CharField(
        max_length=100,
        verbose_name='Template Name (Arabic)',
        help_text='e.g., "ثوب قياسي", "بشت فاخر"'
    )
    description_en = models.TextField(
        blank=True,
        null=True,
        verbose_name='Description (English)',
        help_text='Optional description of this template'
    )
    description_ar = models.TextField(
        blank=True,
        null=True,
        verbose_name='Description (Arabic)',
        help_text='Optional description in Arabic'
    )
    garment_type = models.CharField(
        max_length=50,
        choices=GARMENT_TYPES,
        default='thobe',
        verbose_name='Garment Type'
    )
    is_default = models.BooleanField(
        default=False,
        verbose_name='Default Template',
        help_text='Only one template can be default per garment type'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Active',
        help_text='Inactive templates are hidden from customers'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Measurement Template'
        verbose_name_plural = 'Measurement Templates'
        ordering = ['garment_type', 'name_en']
        indexes = [
            models.Index(fields=['garment_type', 'is_active']),
            models.Index(fields=['is_default', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.name_en} ({self.get_garment_type_display()})"
    
    def clean(self):
        """Ensure only one default template per garment type"""
        if self.is_default:
            # Check if another template is already default for this garment type
            existing_default = MeasurementTemplate.objects.filter(
                garment_type=self.garment_type,
                is_default=True,
                is_active=True
            ).exclude(pk=self.pk)
            
            if existing_default.exists():
                raise ValidationError(
                    f"A default template already exists for {self.get_garment_type_display()}. "
                    f"Please uncheck the default option for '{existing_default.first().name_en}' first."
                )
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    def get_active_fields(self):
        """Get all active measurement fields ordered by display order"""
        return self.fields.filter(is_active=True).order_by('order')
    
    @property
    def field_count(self):
        """Count of active fields in this template"""
        return self.fields.filter(is_active=True).count()


class MeasurementField(models.Model):
    """
    Individual measurement field within a template
    (e.g., "Chest", "Shoulder Width", "Thobe Length")
    """
    UNIT_CHOICES = [
        ('cm', 'Centimeters (cm)'),
        ('inch', 'Inches (in)'),
        ('m', 'Meters (m)'),
    ]
    
    CATEGORY_CHOICES = [
        ('upper_body', 'Upper Body'),
        ('lower_body', 'Lower Body'),
        ('length', 'Length'),
        ('width', 'Width'),
        ('circumference', 'Circumference'),
        ('other', 'Other'),
    ]
    
    template = models.ForeignKey(
        MeasurementTemplate,
        on_delete=models.CASCADE,
        related_name='fields',
        verbose_name='Template'
    )
    field_key = models.CharField(
        max_length=50,
        verbose_name='Field Key',
        help_text='Unique identifier (e.g., "chest", "shoulder_width"). Use lowercase and underscores.'
    )
    display_name_en = models.CharField(
        max_length=100,
        verbose_name='Display Name (English)',
        help_text='e.g., "Chest", "Shoulder Width"'
    )
    display_name_ar = models.CharField(
        max_length=100,
        verbose_name='Display Name (Arabic)',
        help_text='e.g., "الصدر", "عرض الكتف"'
    )
    unit = models.CharField(
        max_length=10,
        choices=UNIT_CHOICES,
        default='cm',
        verbose_name='Unit of Measurement'
    )
    min_value = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name='Minimum Value',
        help_text='Minimum acceptable value for validation'
    )
    max_value = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name='Maximum Value',
        help_text='Maximum acceptable value for validation'
    )
    is_required = models.BooleanField(
        default=True,
        verbose_name='Required Field',
        help_text='If checked, this field must be filled by customer'
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name='Display Order',
        help_text='Lower numbers appear first. Use multiples of 10 for easy reordering.'
    )
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        default='other',
        verbose_name='Category',
        help_text='Group related measurements together'
    )
    help_text_en = models.TextField(
        blank=True,
        null=True,
        verbose_name='Help Text (English)',
        help_text='Optional guidance on how to measure this field'
    )
    help_text_ar = models.TextField(
        blank=True,
        null=True,
        verbose_name='Help Text (Arabic)',
        help_text='Optional measurement guidance in Arabic'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Active',
        help_text='Inactive fields are hidden from customers'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Measurement Field'
        verbose_name_plural = 'Measurement Fields'
        ordering = ['template', 'order', 'field_key']
        unique_together = ['template', 'field_key']
        indexes = [
            models.Index(fields=['template', 'is_active', 'order']),
        ]
    
    def __str__(self):
        return f"{self.display_name_en} ({self.template.name_en})"
    
    def clean(self):
        """Validate field configuration"""
        errors = {}
        
        # Validate min < max
        if self.min_value >= self.max_value:
            errors['min_value'] = 'Minimum value must be less than maximum value'
            errors['max_value'] = 'Maximum value must be greater than minimum value'
        
        # Validate field_key format (lowercase, underscores only)
        import re
        if not re.match(r'^[a-z][a-z0-9_]*$', self.field_key):
            errors['field_key'] = (
                'Field key must start with a letter and contain only lowercase letters, '
                'numbers, and underscores (e.g., "chest", "shoulder_width")'
            )
        
        # Check for duplicate field_key in same template
        if self.template_id:
            duplicate = MeasurementField.objects.filter(
                template=self.template,
                field_key=self.field_key
            ).exclude(pk=self.pk)
            
            if duplicate.exists():
                errors['field_key'] = (
                    f'A field with key "{self.field_key}" already exists in this template'
                )
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    def validate_value(self, value):
        """
        Validate a measurement value against this field's constraints
        
        Args:
            value: The measurement value to validate
            
        Returns:
            tuple: (is_valid, error_message)
        """
        try:
            decimal_value = float(value)
        except (TypeError, ValueError):
            return False, f"Invalid value for {self.display_name_en}"
        
        if decimal_value < float(self.min_value):
            return False, f"{self.display_name_en} must be at least {self.min_value} {self.unit}"
        
        if decimal_value > float(self.max_value):
            return False, f"{self.display_name_en} must not exceed {self.max_value} {self.unit}"
        
        return True, None
