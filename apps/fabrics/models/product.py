import uuid

from django.conf import settings
from django.db import models

from apps.core.models import BaseModel
from apps.tailors.models.base import IMAGE_VALIDATOR, SEASON_CHOICES


class FabricProduct(BaseModel):
    """Business-level master fabric catalog."""

    APPROVAL_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    business = models.ForeignKey(
        'tailors.Business',
        on_delete=models.CASCADE,
        related_name='fabric_products',
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    sku = models.CharField(max_length=24, unique=True, editable=False)
    fabric_type = models.ForeignKey(
        'tailors.FabricType',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='v2_products',
    )
    category = models.ForeignKey(
        'tailors.FabricCategory',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='v2_products',
    )
    country = models.ForeignKey(
        'tailors.FabricCountry',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='v2_products',
    )
    tags = models.ManyToManyField(
        'tailors.FabricTag',
        blank=True,
        related_name='v2_products',
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stitching_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    seasons = models.CharField(
        max_length=20,
        choices=SEASON_CHOICES,
        default='all_season',
    )
    approval_status = models.CharField(
        max_length=20,
        choices=APPROVAL_CHOICES,
        default='approved',
    )
    is_active = models.BooleanField(default=True, db_index=True)
    is_on_sale = models.BooleanField(default=False)
    discount_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    sale_start = models.DateTimeField(null=True, blank=True)
    sale_end = models.DateTimeField(null=True, blank=True)
    is_featured = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_fabric_products',
    )

    class Meta:
        db_table = 'tailors_fabricproduct'
        verbose_name = 'Fabric Product'
        verbose_name_plural = 'Fabric Products'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['business', 'is_active'], name='tailors_fab_busines_7977f6_idx'),
            models.Index(fields=['business', 'approval_status'], name='tailors_fab_busines_6a90d8_idx'),
        ]

    def save(self, *args, **kwargs):
        if not self.sku:
            self.sku = f'FP-{uuid.uuid4().hex[:8].upper()}'
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.name} ({self.sku})'


class FabricProductImage(models.Model):
    product = models.ForeignKey(
        FabricProduct,
        on_delete=models.CASCADE,
        related_name='gallery',
    )
    image = models.ImageField(
        upload_to='fabrics/v2/products/',
        validators=IMAGE_VALIDATOR,
    )
    is_primary = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tailors_fabricproductimage'
        ordering = ['-is_primary', 'order', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['product'],
                condition=models.Q(is_primary=True),
                name='uniq_v2_primary_image_per_product',
            ),
        ]

    def save(self, *args, **kwargs):
        if self.is_primary:
            FabricProductImage.objects.filter(
                product=self.product,
                is_primary=True,
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)
