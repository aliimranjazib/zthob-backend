from django.contrib import admin
from django.utils.html import format_html
from .models import CustomStyleCategory, CustomStyle


@admin.register(CustomStyleCategory)
class CustomStyleCategoryAdmin(admin.ModelAdmin):
    """
    Admin interface for managing custom style categories
    """
    list_display = ['display_name', 'name', 'display_order', 'is_active', 'styles_count', 'created_at']
    list_editable = ['display_order', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'display_name']
    ordering = ['display_order', 'name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'display_name')
        }),
        ('Display Settings', {
            'fields': ('display_order', 'is_active')
        }),
    )
    
    def styles_count(self, obj):
        """Show count of active styles in this category"""
        count = obj.styles.filter(is_active=True).count()
        total = obj.styles.count()
        return f"{count} active / {total} total"
    styles_count.short_description = 'Styles'


@admin.register(CustomStyle)
class CustomStyleAdmin(admin.ModelAdmin):
    """
    Admin interface for managing individual custom styles
    """
    list_display = [
        'name', 
        'category', 
        'code', 
        'image_preview', 
        'display_order', 
        'extra_price', 
        'is_active',
        'created_at'
    ]
    list_editable = ['display_order', 'is_active', 'extra_price']
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['name', 'code', 'description']
    ordering = ['category__display_order', 'display_order', 'name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('category', 'name', 'code', 'description')
        }),
        ('Image', {
            'fields': ('image', 'image_preview_large'),
            'description': 'Upload style image (PNG/JPG recommended)'
        }),
        ('Display & Pricing', {
            'fields': ('display_order', 'is_active', 'extra_price')
        }),
    )
    
    readonly_fields = ['image_preview_large']
    
    def image_preview(self, obj):
        """Show small image preview in list view"""
        if obj.image:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit: contain;" />',
                obj.image.url
            )
        return '-'
    image_preview.short_description = 'Preview'
    
    def image_preview_large(self, obj):
        """Show larger image preview in detail view"""
        if obj.image:
            return format_html(
                '<img src="{}" width="200" height="200" style="object-fit: contain; border: 1px solid #ddd; padding: 5px;" />',
                obj.image.url
            )
        return 'No image uploaded'
    image_preview_large.short_description = 'Image Preview'
