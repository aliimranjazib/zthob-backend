from django.contrib import admin

from apps.fabrics.models import (
    FabricProduct,
    FabricProductImage,
    FabricStockMovement,
    ShopFabric,
)


class FabricProductImageInline(admin.TabularInline):
    model = FabricProductImage
    extra = 0


@admin.register(FabricProduct)
class FabricProductAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'sku',
        'business',
        'price',
        'is_active',
        'approval_status',
        'is_on_sale',
        'is_featured',
        'created_at',
    )
    list_filter = ('is_active', 'approval_status', 'is_on_sale', 'is_featured', 'seasons')
    search_fields = ('name', 'sku', 'business__name')
    readonly_fields = ('sku', 'created_at', 'updated_at')
    inlines = [FabricProductImageInline]


@admin.register(ShopFabric)
class ShopFabricAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'shop',
        'product',
        'stock',
        'is_visible',
        'is_active',
        'legacy_fabric',
        'updated_at',
    )
    list_filter = ('is_active', 'is_visible')
    search_fields = ('product__name', 'product__sku', 'shop__name')
    raw_id_fields = ('shop', 'product', 'legacy_fabric', 'created_by')


@admin.register(FabricStockMovement)
class FabricStockMovementAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'shop_fabric',
        'movement_type',
        'quantity',
        'previous_stock',
        'new_stock',
        'order_id',
        'created_at',
    )
    list_filter = ('movement_type',)
    search_fields = ('shop_fabric__product__name', 'reason', 'note')
    raw_id_fields = ('shop_fabric', 'created_by')
