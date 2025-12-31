from django.contrib import admin
from django.utils.html import format_html
from .models import CustomStyleCategory, CustomStyle, UserStylePreset


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


@admin.register(UserStylePreset)
class UserStylePresetAdmin(admin.ModelAdmin):
    """
    Admin interface for managing user style presets
    """
    list_display = [
        'name',
        'user',
        'is_default',
        'usage_count',
        'styles_count',
        'created_at'
    ]
    list_filter = ['is_default', 'created_at', 'user']
    search_fields = ['name', 'description', 'user__username', 'user__email']
    ordering = ['-created_at']
    readonly_fields = ['usage_count', 'created_at', 'updated_at', 'styles_preview']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'name', 'description')
        }),
        ('Styles', {
            'fields': ('styles', 'styles_preview'),
            'description': 'Selected style combinations for this preset'
        }),
        ('Settings', {
            'fields': ('is_default', 'usage_count')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def styles_count(self, obj):
        """Show number of styles in this preset"""
        if obj.styles:
            return len(obj.styles)
        return 0
    styles_count.short_description = 'Styles'
    
    def styles_preview(self, obj):
        """Show preview of selected styles"""
        if not obj.styles:
            return 'No styles selected'
        
        html = '<ul>'
        for selection in obj.styles:
            category = selection.get('category', 'Unknown')
            style_id = selection.get('style_id', 'N/A')
            
            try:
                from .models import CustomStyle
                style = CustomStyle.objects.get(id=style_id)
                html += f'<li><strong>{category.title()}:</strong> {style.name} (ID: {style_id})</li>'
            except CustomStyle.DoesNotExist:
                html += f'<li><strong>{category.title()}:</strong> Style ID {style_id} (Not found)</li>'
        
        html += '</ul>'
        return format_html(html)
    styles_preview.short_description = 'Selected Styles'
