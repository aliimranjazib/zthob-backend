from django.contrib import admin
from .models import FCMDeviceToken, NotificationLog


@admin.register(FCMDeviceToken)
class FCMDeviceTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'device_type', 'device_id', 'is_active', 'last_used_at', 'created_at']
    list_filter = ['device_type', 'is_active', 'created_at']
    search_fields = ['user__username', 'user__email', 'token', 'device_id']
    readonly_fields = ['created_at', 'updated_at', 'last_used_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'notification_type', 'category', 'status', 'sent_at', 'created_at']
    list_filter = ['notification_type', 'status', 'created_at']
    search_fields = ['user__username', 'user__email', 'title', 'body']
    readonly_fields = ['created_at', 'updated_at', 'sent_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'fcm_token')

