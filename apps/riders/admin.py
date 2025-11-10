from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import RiderProfile, RiderOrderAssignment, RiderProfileReview


@admin.register(RiderProfile)
class RiderProfileAdmin(admin.ModelAdmin):
    """Professional Rider Profile Admin Interface"""
    
    list_display = [
        'user_link',
        'full_name',
        'phone_number',
        'vehicle_type',
        'approval_status_badge',
        'is_active_badge',
        'is_available_badge',
        'total_deliveries',
        'rating_display',
        'created_at_formatted'
    ]
    
    list_display_links = ['user_link']
    
    list_filter = [
        'is_active',
        'is_available',
        'vehicle_type',
        'created_at',
    ]
    
    def get_queryset(self, request):
        """Optimize queryset with review status"""
        return super().get_queryset(request).select_related('user').prefetch_related('review')
    
    search_fields = [
        'user__username',
        'user__email',
        'full_name',
        'phone_number',
        'national_id',
        'vehicle_number',
    ]
    
    raw_id_fields = ['user']
    
    readonly_fields = [
        'created_at',
        'updated_at',
        'created_by',
        'total_deliveries',
        'rating',
    ]
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Personal Information', {
            'fields': (
                'full_name',
                'national_id',
            )
        }),
        ('Contact Information', {
            'fields': (
                'phone_number',
                'emergency_contact',
            )
        }),
        ('Vehicle Information', {
            'fields': (
                'vehicle_type',
                'vehicle_number',
            )
        }),
        ('Status', {
            'fields': (
                'is_active',
                'is_available',
            )
        }),
        ('Location Tracking', {
            'fields': (
                'current_latitude',
                'current_longitude',
            ),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': (
                'total_deliveries',
                'rating',
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'created_by'),
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
    
    def approval_status_badge(self, obj):
        """Display approval status"""
        try:
            review_status = obj.review.review_status
            colors = {
                'draft': '#6c757d',
                'pending': '#ffc107',
                'approved': '#28a745',
                'rejected': '#dc3545',
            }
            color = colors.get(review_status, '#6c757d')
            try:
                url = reverse('admin:riders_riderprofilereview_change', args=[obj.review.pk])
                return format_html(
                    '<a href="{}"><span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span></a>',
                    url, color, review_status.title()
                )
            except:
                return format_html(
                    '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
                    color, review_status.title()
                )
        except RiderProfileReview.DoesNotExist:
            return format_html(
                '<span style="background-color: #6c757d; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">Draft</span>'
            )
    approval_status_badge.short_description = 'Approval'
    approval_status_badge.admin_order_field = 'review__review_status'
    
    def is_active_badge(self, obj):
        """Display active status"""
        if obj.is_active:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">Active</span>'
            )
        return format_html(
            '<span style="background-color: #dc3545; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">Inactive</span>'
        )
    is_active_badge.short_description = 'Active'
    is_active_badge.admin_order_field = 'is_active'
    
    def is_available_badge(self, obj):
        """Display available status"""
        if obj.is_available:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">Available</span>'
            )
        return format_html(
            '<span style="background-color: #ffc107; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">Busy</span>'
        )
    is_available_badge.short_description = 'Available'
    is_available_badge.admin_order_field = 'is_available'
    
    def rating_display(self, obj):
        """Display rating"""
        if obj.rating:
            color = '#28a745' if obj.rating >= 4.0 else '#ffc107' if obj.rating >= 3.0 else '#dc3545'
            return format_html(
                '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px; font-weight: bold;">{:.2f} ⭐</span>',
                color,
                float(obj.rating)
            )
        return format_html('<em style="color: #999;">No rating</em>')
    rating_display.short_description = 'Rating'
    rating_display.admin_order_field = 'rating'
    
    def created_at_formatted(self, obj):
        """Format creation date"""
        try:
            if obj.created_at:
                return obj.created_at.strftime('%Y-%m-%d %H:%M')
        except (AttributeError, ValueError):
            pass
        return '-'
    created_at_formatted.short_description = 'Created'
    created_at_formatted.admin_order_field = 'created_at'


@admin.register(RiderOrderAssignment)
class RiderOrderAssignmentAdmin(admin.ModelAdmin):
    """Professional Rider Order Assignment Admin Interface"""
    
    list_display = [
        'order_link',
        'rider_link',
        'status_badge',
        'accepted_at_formatted',
        'completed_at_formatted',
    ]
    
    list_display_links = ['order_link']
    
    list_filter = [
        'status',
        'accepted_at',
        'completed_at',
        'created_at',
    ]
    
    search_fields = [
        'order__order_number',
        'rider__username',
        'rider__email',
    ]
    
    raw_id_fields = ['order', 'rider']
    
    readonly_fields = [
        'created_at',
        'updated_at',
        'created_by',
    ]
    
    fieldsets = (
        ('Assignment Information', {
            'fields': (
                'order',
                'rider',
                'status',
            )
        }),
        ('Timeline', {
            'fields': (
                'accepted_at',
                'started_at',
                'completed_at',
            )
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    list_per_page = 50
    
    def order_link(self, obj):
        """Clickable order link"""
        if obj.order and obj.order.pk:
            try:
                url = reverse('admin:orders_order_change', args=[obj.order.pk])
                return format_html('<a href="{}">{}</a>', url, obj.order.order_number or 'No number')
            except Exception:
                return obj.order.order_number or '-'
        return '-'
    order_link.short_description = 'Order'
    order_link.admin_order_field = 'order__order_number'
    
    def rider_link(self, obj):
        """Clickable rider link"""
        if obj.rider and obj.rider.pk:
            try:
                url = reverse('admin:accounts_customuser_change', args=[obj.rider.pk])
                return format_html('<a href="{}">{}</a>', url, obj.rider.username or 'No username')
            except Exception:
                return obj.rider.username or '-'
        return '-'
    rider_link.short_description = 'Rider'
    rider_link.admin_order_field = 'rider__username'
    
    def status_badge(self, obj):
        """Display status with badge"""
        colors = {
            'pending': '#ffc107',
            'accepted': '#17a2b8',
            'in_progress': '#6c757d',
            'completed': '#28a745',
            'cancelled': '#dc3545',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 10px; border-radius: 4px; font-size: 11px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'
    
    def accepted_at_formatted(self, obj):
        """Format accepted date"""
        if obj.accepted_at:
            return obj.accepted_at.strftime('%Y-%m-%d %H:%M')
        return '-'
    accepted_at_formatted.short_description = 'Accepted'
    accepted_at_formatted.admin_order_field = 'accepted_at'
    
    def completed_at_formatted(self, obj):
        """Format completed date"""
        if obj.completed_at:
            return obj.completed_at.strftime('%Y-%m-%d %H:%M')
        return format_html('<em style="color: #999;">Not completed</em>')
    completed_at_formatted.short_description = 'Completed'
    completed_at_formatted.admin_order_field = 'completed_at'


@admin.register(RiderProfileReview)
class RiderProfileReviewAdmin(admin.ModelAdmin):
    """Professional Rider Profile Review Admin Interface"""
    
    list_display = [
        'rider_name_link',
        'user_email',
        'review_status_badge',
        'submitted_at_formatted',
        'reviewed_at_formatted',
        'reviewed_by_link',
    ]
    
    list_display_links = ['rider_name_link']
    
    list_filter = [
        'review_status',
        'submitted_at',
        'reviewed_at',
        'created_at',
    ]
    
    search_fields = [
        'profile__user__username',
        'profile__user__email',
        'profile__full_name',
        'profile__national_id',
        'rejection_reason',
    ]
    
    raw_id_fields = ['profile', 'reviewed_by']
    
    readonly_fields = [
        'created_at',
        'updated_at',
    ]
    
    fieldsets = (
        ('Rider Information', {
            'fields': ('profile',)
        }),
        ('Review Status', {
            'fields': (
                'review_status',
                'rejection_reason',
            )
        }),
        ('Review Timeline', {
            'fields': (
                'submitted_at',
                'reviewed_at',
                'reviewed_by',
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    list_per_page = 50
    
    actions = ['approve_profiles', 'reject_profiles']
    
    def rider_name_link(self, obj):
        """Clickable rider name link"""
        if obj.profile and obj.profile.pk:
            try:
                url = reverse('admin:riders_riderprofile_change', args=[obj.profile.pk])
                name = obj.profile.full_name or obj.profile.user.username if obj.profile.user else 'Unknown'
                return format_html('<a href="{}">{}</a>', url, name)
            except Exception:
                return obj.profile.full_name or '-'
        return '-'
    rider_name_link.short_description = 'Rider Name'
    rider_name_link.admin_order_field = 'profile__full_name'
    
    def user_email(self, obj):
        """User email"""
        if obj.profile and obj.profile.user:
            return obj.profile.user.email
        return '-'
    user_email.short_description = 'Email'
    user_email.admin_order_field = 'profile__user__email'
    
    def review_status_badge(self, obj):
        """Display review status with badge"""
        colors = {
            'draft': '#6c757d',
            'pending': '#ffc107',
            'approved': '#28a745',
            'rejected': '#dc3545',
        }
        color = colors.get(obj.review_status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 10px; border-radius: 4px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.get_review_status_display()
        )
    review_status_badge.short_description = 'Status'
    review_status_badge.admin_order_field = 'review_status'
    
    def submitted_at_formatted(self, obj):
        """Format submitted date"""
        if obj.submitted_at:
            return obj.submitted_at.strftime('%Y-%m-%d %H:%M')
        return format_html('<em style="color: #999;">Not submitted</em>')
    submitted_at_formatted.short_description = 'Submitted'
    submitted_at_formatted.admin_order_field = 'submitted_at'
    
    def reviewed_at_formatted(self, obj):
        """Format reviewed date"""
        if obj.reviewed_at:
            return obj.reviewed_at.strftime('%Y-%m-%d %H:%M')
        return format_html('<em style="color: #999;">Not reviewed</em>')
    reviewed_at_formatted.short_description = 'Reviewed'
    reviewed_at_formatted.admin_order_field = 'reviewed_at'
    
    def reviewed_by_link(self, obj):
        """Clickable reviewer link"""
        if obj.reviewed_by and obj.reviewed_by.pk:
            try:
                url = reverse('admin:accounts_customuser_change', args=[obj.reviewed_by.pk])
                return format_html('<a href="{}">{}</a>', url, obj.reviewed_by.username or 'No username')
            except Exception:
                return obj.reviewed_by.username or '-'
        return format_html('<em style="color: #999;">Not reviewed</em>')
    reviewed_by_link.short_description = 'Reviewed By'
    reviewed_by_link.admin_order_field = 'reviewed_by__username'
    
    def approve_profiles(self, request, queryset):
        """Bulk approve rider profiles"""
        from django.utils import timezone
        updated = queryset.filter(review_status='pending').update(
            review_status='approved',
            reviewed_at=timezone.now(),
            reviewed_by=request.user
        )
        self.message_user(request, f'{updated} rider profile(s) approved successfully.')
    approve_profiles.short_description = "Approve selected rider profiles"
    
    def reject_profiles(self, request, queryset):
        """Bulk reject rider profiles"""
        from django.utils import timezone
        updated = queryset.filter(review_status='pending').update(
            review_status='rejected',
            reviewed_at=timezone.now(),
            reviewed_by=request.user
        )
        self.message_user(request, f'{updated} rider profile(s) rejected. Please add rejection reasons manually.')
    reject_profiles.short_description = "Reject selected rider profiles"
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related(
            'profile__user',
            'reviewed_by'
        )

