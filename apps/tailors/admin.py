from django.contrib import admin
from .models import TailorProfile, FabricCategory, Fabric, FabricImage

# Register your models here.
@admin.register(TailorProfile)
class TailorProfileAdmin(admin.ModelAdmin):
    # Essential tailor info
    list_display = ['user', 'shop_name', 'contact_number', 'shop_status']
    list_filter = ['shop_status']
    search_fields = ['user__username', 'shop_name', 'contact_number']
    raw_id_fields = ['user']
    readonly_fields = ['created_at', 'updated_at']
    
    # Grouped fields
    fieldsets = (
        ('Basic Info', {'fields': ('user', 'shop_name', 'contact_number')}),
        ('Business Details', {'fields': ('establishment_year', 'tailor_experience', 'working_hours')}),
        ('Location', {'fields': ('address',)}),
        ('Status', {'fields': ('shop_status',)}),
    )

@admin.register(FabricCategory)
class FabricCategoryAdmin(admin.ModelAdmin):
    # Simple category management
    list_display = ['name', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at']
    
    # Simple form
    fieldsets = (
        ('Category Info', {'fields': ('name', 'slug', 'is_active')}),
    )

@admin.register(Fabric)
class FabricAdmin(admin.ModelAdmin):
    # Essential fabric info
    list_display = ['name', 'tailor', 'category', 'price', 'stock', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['name', 'sku', 'tailor__shop_name']
    raw_id_fields = ['tailor', 'category']
    readonly_fields = ['sku', 'created_at', 'updated_at']
    
    # Grouped fabric form
    fieldsets = (
        ('Basic Info', {'fields': ('name', 'description', 'category', 'tailor')}),
        ('Pricing & Stock', {'fields': ('price', 'stock', 'is_active')}),
        ('Images', {'fields': ('fabric_image',)}),
    )

@admin.register(FabricImage)
class FabricImageAdmin(admin.ModelAdmin):
    # Simple image management
    list_display = ['fabric', 'is_primary', 'order']
    list_filter = ['is_primary']
    search_fields = ['fabric__name']
    raw_id_fields = ['fabric']
    readonly_fields = ['created_at']
    
    # Simple image form
    fieldsets = (
        ('Image Info', {'fields': ('fabric', 'image', 'is_primary', 'order')}),
    )
