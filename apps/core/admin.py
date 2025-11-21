from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import SystemSettings, Slider, PhoneVerification


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
    
    list_display_links = ['id', 'tax_rate_percentage']  # Make ID clickable to edit
    
    list_filter = ['is_active', 'updated_at']
    
    search_fields = [
        'notes',
        'updated_by__username',
        'updated_by__email',
    ]
    
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
    
    readonly_fields = ['created_at', 'updated_at', 'updated_by']
    
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
    
    def has_change_permission(self, request, obj=None):
        """Allow editing of system settings"""
        return super().has_change_permission(request, obj)
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of active settings"""
        if obj and obj.is_active:
            return False
        return super().has_delete_permission(request, obj)
    
    def get_readonly_fields(self, request, obj=None):
        """Return readonly fields - ensure editable fields are not readonly"""
        readonly = list(super().get_readonly_fields(request, obj))
        # Make sure all fields in fieldsets are editable (except metadata)
        return readonly


@admin.register(Slider)
class SliderAdmin(admin.ModelAdmin):
    """Admin interface for Slider/Banner management"""
    
    list_display = [
        'id',
        'image_preview',
        'title',
        'button_text',
        'order',
        'is_active_badge',
        'created_at_formatted'
    ]
    
    list_display_links = ['title']
    
    list_filter = ['is_active', 'created_at']
    
    search_fields = ['title', 'description', 'button_text']
    
    readonly_fields = ['created_at', 'updated_at', 'image_preview_detail']
    
    fieldsets = (
        ('Slider Content', {
            'fields': (
                'title',
                'description',
                'image',
                'image_preview_detail',
            )
        }),
        ('Button Settings', {
            'fields': (
                'button_text',
                'button_link',
            ),
            'description': 'Optional button to display on the slider'
        }),
        ('Display Settings', {
            'fields': (
                'order',
                'is_active',
            )
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def image_preview(self, obj):
        """Display image preview in list view"""
        if obj.image:
            try:
                return format_html(
                    '<img src="{}" width="80" height="50" style="border-radius: 5px; object-fit: cover;" />',
                    obj.image.url
                )
            except (ValueError, AttributeError):
                return format_html('<em style="color: #999;">Invalid image</em>')
        return format_html('<em style="color: #999;">No image</em>')
    image_preview.short_description = 'Preview'
    
    def image_preview_detail(self, obj):
        """Display larger image preview in detail view"""
        if obj.image:
            try:
                return format_html(
                    '<img src="{}" width="400" height="250" style="border-radius: 8px; object-fit: cover; border: 2px solid #ddd;" />',
                    obj.image.url
                )
            except (ValueError, AttributeError):
                return format_html('<em style="color: #999;">Invalid image</em>')
        return format_html('<em style="color: #999;">No image</em>')
    image_preview_detail.short_description = 'Image Preview'
    
    def is_active_badge(self, obj):
        """Display active status with badge"""
        if obj.is_active:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">Active</span>'
            )
        return format_html(
            '<span style="background-color: #dc3545; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">Inactive</span>'
        )
    is_active_badge.short_description = 'Status'
    is_active_badge.admin_order_field = 'is_active'
    
    def created_at_formatted(self, obj):
        """Format creation date"""
        return obj.created_at.strftime('%Y-%m-%d %H:%M')
    created_at_formatted.short_description = 'Created'
    created_at_formatted.admin_order_field = 'created_at'
    
    def save_model(self, request, obj, form, change):
        """Set created_by when creating new slider"""
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    list_per_page = 50


@admin.register(PhoneVerification)
class PhoneVerificationAdmin(admin.ModelAdmin):
    """Admin interface for Phone Verification OTP records"""
    
    list_display = [
        'user_link',
        'phone_number',
        'otp_code',
        'is_verified_badge',
        'is_expired_badge',
        'expires_at_formatted',
        'created_at_formatted'
    ]
    
    list_display_links = ['user_link']
    
    list_filter = [
        'is_verified',
        'created_at',
        'expires_at',
    ]
    
    search_fields = [
        'user__username',
        'user__email',
        'phone_number',
        'otp_code',
    ]
    
    readonly_fields = [
        'created_at',
        'is_expired_display',
        'is_valid_display',
    ]
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Verification Details', {
            'fields': (
                'phone_number',
                'otp_code',
                'is_verified',
            )
        }),
        ('Status', {
            'fields': (
                'is_expired_display',
                'is_valid_display',
            )
        }),
        ('Timestamps', {
            'fields': (
                'expires_at',
                'created_at',
            )
        }),
    )
    
    date_hierarchy = 'created_at'
    
    list_per_page = 50
    
    def user_link(self, obj):
        """Clickable user link"""
        if obj.user and obj.user.pk:
            try:
                url = reverse('admin:accounts_customuser_change', args=[obj.user.pk])
                return format_html('<a href="{}">{}</a>', url, obj.user.username or 'No username')
            except Exception:
                return obj.user.username or '-'
        return '-'
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__username'
    
    def is_verified_badge(self, obj):
        """Display verification status"""
        if obj.is_verified:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">✓ Verified</span>'
            )
        return format_html(
            '<span style="background-color: #ffc107; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">Pending</span>'
        )
    is_verified_badge.short_description = 'Verified'
    is_verified_badge.admin_order_field = 'is_verified'
    
    def is_expired_badge(self, obj):
        """Display expiration status"""
        if obj.is_expired():
            return format_html(
                '<span style="background-color: #dc3545; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">Expired</span>'
            )
        return format_html(
            '<span style="background-color: #28a745; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">Valid</span>'
        )
    is_expired_badge.short_description = 'Expired'
    
    def expires_at_formatted(self, obj):
        """Format expiration date"""
        if obj.expires_at:
            return obj.expires_at.strftime('%Y-%m-%d %H:%M:%S')
        return '-'
    expires_at_formatted.short_description = 'Expires At'
    expires_at_formatted.admin_order_field = 'expires_at'
    
    def created_at_formatted(self, obj):
        """Format creation date"""
        return obj.created_at.strftime('%Y-%m-%d %H:%M:%S')
    created_at_formatted.short_description = 'Created'
    created_at_formatted.admin_order_field = 'created_at'
    
    def is_expired_display(self, obj):
        """Display expiration status in detail view"""
        if obj.is_expired():
            return format_html(
                '<span style="background-color: #dc3545; color: white; padding: 5px 10px; border-radius: 4px; font-weight: bold;">EXPIRED</span>'
            )
        return format_html(
            '<span style="background-color: #28a745; color: white; padding: 5px 10px; border-radius: 4px; font-weight: bold;">VALID</span>'
        )
    is_expired_display.short_description = 'Expiration Status'
    
    def is_valid_display(self, obj):
        """Display validity status in detail view"""
        if obj.is_valid():
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 5px 10px; border-radius: 4px; font-weight: bold;">VALID</span>'
            )
        return format_html(
            '<span style="background-color: #dc3545; color: white; padding: 5px 10px; border-radius: 4px; font-weight: bold;">INVALID</span>'
        )
    is_valid_display.short_description = 'Validity Status'
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related('user')

