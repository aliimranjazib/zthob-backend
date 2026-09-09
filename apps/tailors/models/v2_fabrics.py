import uuid

from django.conf import settings
from django.db import models

from apps.core.models import BaseModel
from apps.tailors.models.base import IMAGE_VALIDATOR, SEASON_CHOICES


class FabricProduct(BaseModel):
    """Business-level master fabric catalog (V2)."""

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
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_fabric_products',
    )

    class Meta:
        verbose_name = 'Fabric Product'
        verbose_name_plural = 'Fabric Products'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['business', 'is_active']),
            models.Index(fields=['business', 'approval_status']),
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


class ShopFabric(BaseModel):
    """Branch-level fabric assignment and stock."""

    shop = models.ForeignKey(
        'tailors.TailorProfile',
        on_delete=models.CASCADE,
        related_name='shop_fabrics',
    )
    product = models.ForeignKey(
        FabricProduct,
        on_delete=models.CASCADE,
        related_name='shop_assignments',
    )
    legacy_fabric = models.OneToOneField(
        'tailors.Fabric',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='v2_shop_fabric',
        help_text='Legacy fabric row used by v1 order/checkout APIs',
    )
    stock = models.PositiveIntegerField(default=0)
    reserved_stock = models.PositiveIntegerField(default=0)
    price_override = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    is_visible = models.BooleanField(default=True, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = 'Shop Fabric'
        verbose_name_plural = 'Shop Fabrics'
        constraints = [
            models.UniqueConstraint(
                fields=['shop', 'product'],
                name='uniq_shop_fabric_product',
            ),
        ]
        indexes = [
            models.Index(fields=['shop', 'is_active', 'is_visible']),
            models.Index(fields=['product', 'is_active']),
        ]

    @property
    def available_stock(self) -> int:
        available = self.stock - self.reserved_stock
        return max(available, 0)

    @property
    def effective_price(self):
        if self.price_override is not None:
            return self.price_override
        return self.product.price

    def __str__(self):
        return f'{self.product.name} @ shop {self.shop_id}'


class FabricStockMovement(models.Model):
    TYPE_SALE = 'sale'
    TYPE_ADJUSTMENT_ADD = 'adjustment_add'
    TYPE_ADJUSTMENT_REMOVE = 'adjustment_remove'
    TYPE_ADJUSTMENT_SET = 'adjustment_set'
    TYPE_ASSIGN = 'assign'

    TYPE_CHOICES = (
        (TYPE_SALE, 'Sale'),
        (TYPE_ADJUSTMENT_ADD, 'Adjustment add'),
        (TYPE_ADJUSTMENT_REMOVE, 'Adjustment remove'),
        (TYPE_ADJUSTMENT_SET, 'Adjustment set'),
        (TYPE_ASSIGN, 'Assign'),
    )

    shop_fabric = models.ForeignKey(
        ShopFabric,
        on_delete=models.CASCADE,
        related_name='stock_movements',
    )
    movement_type = models.CharField(max_length=32, choices=TYPE_CHOICES)
    quantity = models.IntegerField()
    previous_stock = models.PositiveIntegerField()
    new_stock = models.PositiveIntegerField()
    reason = models.CharField(max_length=64, blank=True, default='')
    note = models.TextField(blank=True, default='')
    order_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fabric_stock_movements',
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['shop_fabric', 'movement_type', 'created_at']),
        ]
