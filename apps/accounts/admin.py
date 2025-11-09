from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.contrib import messages
from django.db.models import Q
from .models import CustomUser


# ============================================================================
# CUSTOM FILTERS
# ============================================================================

class RoleFilter(admin.SimpleListFilter):
    """Custom filter for user roles"""
    title = 'User Role'
    parameter_name = 'role_filter'
    
    def lookups(self, request, model_admin):
        return (
            ('active_users', 'Active Users'),
            ('tailors', 'Tailors'),
            ('admins', 'Administrators'),
            ('riders', 'Riders'),
            ('inactive', 'Inactive Users'),
            ('deleted', 'Soft Deleted'),
        )
    
    def queryset(self, request, queryset):
        if self.value() == 'active_users':
            return queryset.filter(role='USER', is_active=True, is_deleted=False)
        elif self.value() == 'tailors':
            return queryset.filter(role='TAILOR', is_active=True)
        elif self.value() == 'admins':
            return queryset.filter(role='ADMIN', is_active=True)
        elif self.value() == 'riders':
            return queryset.filter(role='RIDER', is_active=True)
        elif self.value() == 'inactive':
            return queryset.filter(is_active=False, is_deleted=False)
        elif self.value() == 'deleted':
            return queryset.filter(is_deleted=True)


class PhoneVerificationFilter(admin.SimpleListFilter):
    """Filter for phone verification status"""
    title = 'Phone Verification'
    parameter_name = 'phone_verified'
    
    def lookups(self, request, model_admin):
        return (
            ('verified', 'Verified'),
            ('unverified', 'Unverified'),
        )
    
    def queryset(self, request, queryset):
        if self.value() == 'verified':
            return queryset.filter(phone_verified=True)
        elif self.value() == 'unverified':
            return queryset.filter(phone_verified=False)


# ============================================================================
# USER ADMIN
# ============================================================================

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """
    Professional User Admin Interface
    
    Features:
    - Enhanced display with role badges
    - Custom filters for better user management
    - Bulk actions for common operations
    - Phone verification status
    - Soft delete support
    """
    
    # List Display
    list_display = [
        'username_link',
        'email',
        'full_name_display',
        'role_badge',
        'phone_info',
        'verification_status',
        'is_active_badge',
        'date_joined_formatted',
        'last_login_formatted'
    ]
    
    list_display_links = ['username_link']
    
    # Filtering & Search
    list_filter = [
        RoleFilter,
        PhoneVerificationFilter,
        'role',
        'is_active',
        'is_staff',
        'is_superuser',
        'is_deleted',
        'phone_verified',
        'date_joined',
        'last_login',
    ]
    
    search_fields = [
        'username',
        'email',
        'first_name',
        'last_name',
        'phone',
    ]
    
    date_hierarchy = 'date_joined'
    
    # Fieldsets - Organized for better UX
    fieldsets = (
        ('Authentication', {
            'fields': ('username', 'password'),
            'description': 'User authentication credentials'
        }),
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'email'),
        }),
        ('Contact Information', {
            'fields': ('phone', 'phone_verified'),
        }),
        ('Account Type & Permissions', {
            'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'is_deleted'),
            'description': 'User role and system permissions'
        }),
        ('Important Dates', {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',)
        }),
        ('Groups & Permissions', {
            'fields': ('groups', 'user_permissions'),
            'classes': ('collapse',),
            'description': 'Django groups and permissions'
        }),
    )
    
    # Add form fieldsets
    add_fieldsets = (
        ('Create New User', {
            'classes': ('wide',),
            'fields': (
                'username',
                'email',
                'first_name',
                'last_name',
                'phone',
                'role',
                'password1',
                'password2',
            ),
            'description': 'Required fields for creating a new user account'
        }),
    )
    
    # Readonly fields
    readonly_fields = ['date_joined', 'last_login']
    
    # Actions
    actions = [
        'activate_users',
        'deactivate_users',
        'mark_phone_as_verified',
        'mark_phone_as_unverified',
        'soft_delete_users',
        'restore_deleted_users',
        'export_users_csv',
    ]
    
    # Pagination
    list_per_page = 50
    list_max_show_all = 500
    
    # Custom Display Methods
    def username_link(self, obj):
        """Clickable username linking to detail view"""
        if obj.pk:
            url = reverse('admin:accounts_customuser_change', args=[obj.pk])
            return format_html('<a href="{}"><strong>{}</strong></a>', url, obj.username)
        return obj.username
    username_link.short_description = 'Username'
    username_link.admin_order_field = 'username'
    
    def full_name_display(self, obj):
        """Display full name or username if not available"""
        full_name = obj.get_full_name()
        if full_name:
            return format_html('<strong>{}</strong>', full_name)
        return format_html('<em style="color: #999;">{}</em>', obj.username)
    full_name_display.short_description = 'Full Name'
    full_name_display.admin_order_field = 'first_name'
    
    def role_badge(self, obj):
        """Display role with color-coded badge"""
        colors = {
            'USER': '#17a2b8',
            'TAILOR': '#28a745',
            'ADMIN': '#dc3545',
            'RIDER': '#ffc107',
        }
        color = colors.get(obj.role, '#6c757d')
        role_display = dict(CustomUser.USER_ROLES).get(obj.role, obj.role)
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 10px; border-radius: 4px; font-weight: 500; font-size: 11px;">{}</span>',
            color,
            role_display
        )
    role_badge.short_description = 'Role'
    role_badge.admin_order_field = 'role'
    
    def phone_info(self, obj):
        """Display phone number with verification indicator"""
        if obj.phone:
            verified_icon = '✓' if obj.phone_verified else '✗'
            color = '#28a745' if obj.phone_verified else '#dc3545'
            return format_html(
                '{} <span style="color: {}; font-weight: bold;">{}</span>',
                obj.phone,
                color,
                verified_icon
            )
        return format_html('<em style="color: #999;">No phone</em>')
    phone_info.short_description = 'Phone'
    phone_info.admin_order_field = 'phone'
    
    def verification_status(self, obj):
        """Display verification status"""
        if obj.phone_verified:
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">✓ Verified</span>'
            )
        return format_html(
            '<span style="color: #dc3545;">✗ Unverified</span>'
        )
    verification_status.short_description = 'Verified'
    verification_status.admin_order_field = 'phone_verified'
    
    def is_active_badge(self, obj):
        """Display active status with badge"""
        if obj.is_deleted:
            return format_html(
                '<span style="background-color: #6c757d; color: white; padding: 4px 10px; border-radius: 4px; font-size: 11px;">Deleted</span>'
            )
        elif obj.is_active:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 4px 10px; border-radius: 4px; font-size: 11px;">Active</span>'
            )
        else:
            return format_html(
                '<span style="background-color: #dc3545; color: white; padding: 4px 10px; border-radius: 4px; font-size: 11px;">Inactive</span>'
            )
    is_active_badge.short_description = 'Status'
    is_active_badge.admin_order_field = 'is_active'
    
    def date_joined_formatted(self, obj):
        """Format date joined"""
        if obj.date_joined:
            return obj.date_joined.strftime('%Y-%m-%d %H:%M')
        return '-'
    date_joined_formatted.short_description = 'Joined'
    date_joined_formatted.admin_order_field = 'date_joined'
    
    def last_login_formatted(self, obj):
        """Format last login"""
        if obj.last_login:
            return obj.last_login.strftime('%Y-%m-%d %H:%M')
        return format_html('<em style="color: #999;">Never</em>')
    last_login_formatted.short_description = 'Last Login'
    last_login_formatted.admin_order_field = 'last_login'
    
    # Custom Actions
    def activate_users(self, request, queryset):
        """Bulk action to activate users"""
        count = queryset.filter(is_active=False).update(is_active=True, is_deleted=False)
        self.message_user(
            request,
            f'Successfully activated {count} user(s).',
            messages.SUCCESS
        )
    activate_users.short_description = 'Activate selected users'
    
    def deactivate_users(self, request, queryset):
        """Bulk action to deactivate users"""
        count = queryset.filter(is_active=True, is_deleted=False).update(is_active=False)
        self.message_user(
            request,
            f'Successfully deactivated {count} user(s).',
            messages.SUCCESS
        )
    deactivate_users.short_description = 'Deactivate selected users'
    
    def mark_phone_as_verified(self, request, queryset):
        """Bulk action to mark phone as verified"""
        count = queryset.filter(phone_verified=False).exclude(phone__isnull=True).exclude(phone='').update(phone_verified=True)
        self.message_user(
            request,
            f'Successfully marked {count} user(s) phone as verified.',
            messages.SUCCESS
        )
    mark_phone_as_verified.short_description = 'Mark phone as verified'
    
    def mark_phone_as_unverified(self, request, queryset):
        """Bulk action to mark phone as unverified"""
        count = queryset.filter(phone_verified=True).update(phone_verified=False)
        self.message_user(
            request,
            f'Successfully marked {count} user(s) phone as unverified.',
            messages.SUCCESS
        )
    mark_phone_as_unverified.short_description = 'Mark phone as unverified'
    
    def soft_delete_users(self, request, queryset):
        """Bulk action to soft delete users"""
        count = 0
        for user in queryset.filter(is_deleted=False):
            user.soft_delete()
            count += 1
        self.message_user(
            request,
            f'Successfully soft deleted {count} user(s).',
            messages.SUCCESS
        )
    soft_delete_users.short_description = 'Soft delete selected users'
    
    def restore_deleted_users(self, request, queryset):
        """Bulk action to restore soft deleted users"""
        count = queryset.filter(is_deleted=True).update(
            is_deleted=False,
            is_active=True
        )
        self.message_user(
            request,
            f'Successfully restored {count} user(s).',
            messages.SUCCESS
        )
    restore_deleted_users.short_description = 'Restore deleted users'
    
    def export_users_csv(self, request, queryset):
        """Export selected users to CSV"""
        import csv
        from django.http import HttpResponse
        from datetime import datetime
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="users_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Username',
            'Email',
            'First Name',
            'Last Name',
            'Phone',
            'Phone Verified',
            'Role',
            'Is Active',
            'Is Staff',
            'Is Deleted',
            'Date Joined',
            'Last Login',
        ])
        
        for user in queryset:
            writer.writerow([
                user.username,
                user.email,
                user.first_name or '',
                user.last_name or '',
                user.phone or '',
                'Yes' if user.phone_verified else 'No',
                dict(CustomUser.USER_ROLES).get(user.role, user.role),
                'Yes' if user.is_active else 'No',
                'Yes' if user.is_staff else 'No',
                'Yes' if user.is_deleted else 'No',
                user.date_joined.strftime('%Y-%m-%d %H:%M:%S') if user.date_joined else '',
                user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else '',
            ])
        
        return response
    export_users_csv.short_description = 'Export selected users to CSV'
    
    # Override get_queryset for optimization
    def get_queryset(self, request):
        """Optimize queryset"""
        qs = super().get_queryset(request)
        return qs.select_related().prefetch_related('groups', 'user_permissions')
