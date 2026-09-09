from django.conf import settings
from django.db import models

from apps.core.models import BaseModel


class ShopFabric(BaseModel):
    """Shop-level fabric listing (published product at a branch)."""

    shop = models.ForeignKey(
        'tailors.TailorProfile',
        on_delete=models.CASCADE,
        related_name='shop_fabrics',
    )
    product = models.ForeignKey(
        'fabrics.FabricProduct',
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
        db_table = 'tailors_shopfabric'
        verbose_name = 'Shop Fabric'
        verbose_name_plural = 'Shop Fabrics'
        constraints = [
            models.UniqueConstraint(
                fields=['shop', 'product'],
                name='uniq_shop_fabric_product',
            ),
        ]
        indexes = [
            models.Index(fields=['shop', 'is_active', 'is_visible'], name='tailors_sho_shop_id_7766f3_idx'),
            models.Index(fields=['product', 'is_active'], name='tailors_sho_product_ea359b_idx'),
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
        db_table = 'tailors_fabricstockmovement'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['shop_fabric', 'movement_type', 'created_at'], name='tailors_fab_shop_fa_7724e2_idx'),
        ]
