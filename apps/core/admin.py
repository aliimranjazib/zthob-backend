from django.contrib import admin
from .models import SystemSettings


@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    """Admin interface for System Settings"""
    
    list_display = [
        'id',
        'tax_rate_percentage',
        'delivery_fee_under_10km',
        'delivery_fee_10km_and_above',
        'distance_threshold_km',
        'free_delivery_threshold',
        'is_active',
        'updated_at',
        'updated_by'
    ]
    
    list_filter = ['is_active', 'updated_at']
    
    fieldsets = (
        ('Tax/VAT Settings', {
            'fields': ('tax_rate',)
        }),
        ('Delivery Fee Settings', {
            'fields': (
                'delivery_fee_under_10km',
                'delivery_fee_10km_and_above',
                'distance_threshold_km',
            ),
            'description': 'Configure delivery fees based on distance'
        }),
        ('Free Delivery Settings', {
            'fields': ('free_delivery_threshold',),
            'description': 'Set the order subtotal threshold for free delivery. Set to 0 to disable.'
        }),
        ('Status', {
            'fields': ('is_active', 'notes')
        }),
        ('Metadata', {
            'fields': ('updated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def tax_rate_percentage(self, obj):
        """Display tax rate as percentage"""
        return f"{obj.tax_rate * 100:.2f}%"
    tax_rate_percentage.short_description = "Tax Rate"
    
    def save_model(self, request, obj, form, change):
        """Set updated_by to current user"""
        if not change:
            obj.updated_by = request.user
        else:
            obj.updated_by = request.user
        super().save_model(request, obj, form, change)
    
    def has_add_permission(self, request):
        """Allow adding only if no active settings exist"""
        if SystemSettings.objects.filter(is_active=True).exists():
            return False
        return super().has_add_permission(request)
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of active settings"""
        if obj and obj.is_active:
            return False
        return super().has_delete_permission(request, obj)

