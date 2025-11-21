from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import FCMDeviceToken, NotificationLog


@admin.register(FCMDeviceToken)
class FCMDeviceTokenAdmin(admin.ModelAdmin):
    """Professional FCM Device Token Admin Interface"""
    
    list_display = [
        'user_link',
        'device_type_badge',
        'device_id',
        'is_active_badge',
        'last_used_at_formatted',
        'created_at_formatted'
    ]
    
    list_display_links = ['user_link']
    
    list_filter = ['device_type', 'is_active', 'created_at']
    
    search_fields = [
        'user__username',
        'user__email',
        'token',
        'device_id'
    ]
    
    readonly_fields = [
        'created_at',
        'updated_at',
        'last_used_at',
    ]
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Device Information', {
            'fields': (
                'device_type',
                'device_id',
                'token',
            )
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': (
                'last_used_at',
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',)
        }),
    )
    
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
    
    def device_type_badge(self, obj):
        """Display device type with badge"""
        colors = {
            'ios': '#007AFF',
            'android': '#3DDC84',
            'web': '#4285F4',
        }
        color = colors.get(obj.device_type.lower(), '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.device_type.upper()
        )
    device_type_badge.short_description = 'Device Type'
    device_type_badge.admin_order_field = 'device_type'
    
    def is_active_badge(self, obj):
        """Display active status"""
        if obj.is_active:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">Active</span>'
            )
        return format_html(
            '<span style="background-color: #dc3545; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">Inactive</span>'
        )
    is_active_badge.short_description = 'Status'
    is_active_badge.admin_order_field = 'is_active'
    
    def last_used_at_formatted(self, obj):
        """Format last used date"""
        if obj.last_used_at:
            return obj.last_used_at.strftime('%Y-%m-%d %H:%M')
        return format_html('<em style="color: #999;">Never</em>')
    last_used_at_formatted.short_description = 'Last Used'
    last_used_at_formatted.admin_order_field = 'last_used_at'
    
    def created_at_formatted(self, obj):
        """Format creation date"""
        return obj.created_at.strftime('%Y-%m-%d %H:%M')
    created_at_formatted.short_description = 'Created'
    created_at_formatted.admin_order_field = 'created_at'
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related('user')


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    """Professional Notification Log Admin Interface"""
    
    list_display = [
        'user_link',
        'notification_type_badge',
        'category_badge',
        'status_badge',
        'title_preview',
        'sent_at_formatted',
        'created_at_formatted'
    ]
    
    list_display_links = ['user_link']
    
    list_filter = [
        'notification_type',
        'category',
        'status',
        'created_at',
        'sent_at',
    ]
    
    search_fields = [
        'user__username',
        'user__email',
        'title',
        'body',
        'data',
    ]
    
    readonly_fields = [
        'created_at',
        'updated_at',
        'sent_at',
        'title_preview',
        'body_preview',
    ]
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'fcm_token')
        }),
        ('Notification Details', {
            'fields': (
                'notification_type',
                'category',
                'title',
                'title_preview',
                'body',
                'body_preview',
            )
        }),
        ('Additional Data', {
            'fields': ('data',),
            'classes': ('collapse',)
        }),
        ('Status & Delivery', {
            'fields': (
                'status',
                'sent_at',
                'error_message',
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',)
        }),
    )
    
    list_per_page = 50
    
    date_hierarchy = 'created_at'
    
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
    
    def notification_type_badge(self, obj):
        """Display notification type with badge"""
        colors = {
            'push': '#28a745',
            'email': '#17a2b8',
            'sms': '#ffc107',
        }
        color = colors.get(obj.notification_type.lower(), '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.notification_type.upper()
        )
    notification_type_badge.short_description = 'Type'
    notification_type_badge.admin_order_field = 'notification_type'
    
    def category_badge(self, obj):
        """Display category with badge"""
        colors = {
            'order': '#3498db',
            'promotion': '#e74c3c',
            'system': '#95a5a6',
            'account': '#9b59b6',
        }
        color = colors.get(obj.category.lower() if obj.category else '', '#6c757d')
        category_display = obj.category or 'N/A'
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            category_display
        )
    category_badge.short_description = 'Category'
    category_badge.admin_order_field = 'category'
    
    def status_badge(self, obj):
        """Display status with badge"""
        colors = {
            'sent': '#28a745',
            'failed': '#dc3545',
            'pending': '#ffc107',
        }
        color = colors.get(obj.status.lower() if obj.status else '', '#6c757d')
        status_display = obj.status or 'N/A'
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            status_display.upper()
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'
    
    def title_preview(self, obj):
        """Preview of title"""
        if obj.title:
            preview = obj.title[:50] + '...' if len(obj.title) > 50 else obj.title
            return format_html('<strong>{}</strong>', preview)
        return format_html('<em style="color: #999;">No title</em>')
    title_preview.short_description = 'Title Preview'
    
    def body_preview(self, obj):
        """Preview of body"""
        if obj.body:
            preview = obj.body[:100] + '...' if len(obj.body) > 100 else obj.body
            return format_html('<small>{}</small>', preview)
        return format_html('<em style="color: #999;">No body</em>')
    body_preview.short_description = 'Body Preview'
    
    def sent_at_formatted(self, obj):
        """Format sent date"""
        if obj.sent_at:
            return obj.sent_at.strftime('%Y-%m-%d %H:%M')
        return format_html('<em style="color: #999;">Not sent</em>')
    sent_at_formatted.short_description = 'Sent At'
    sent_at_formatted.admin_order_field = 'sent_at'
    
    def created_at_formatted(self, obj):
        """Format creation date"""
        return obj.created_at.strftime('%Y-%m-%d %H:%M')
    created_at_formatted.short_description = 'Created'
    created_at_formatted.admin_order_field = 'created_at'
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related('user', 'fcm_token')

