from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from . import models
from .models import (
    RiderProfile, RiderOrderAssignment, RiderProfileReview, RiderDocument,
    TailorInvitationCode, TailorRiderAssociation
)


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
        'iqama_number',
        'license_number',
        'vehicle_plate_number_english',
        'vehicle_plate_number_arabic',
        'vehicle_registration_number',
        'insurance_policy_number',
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
                'phone_number',
                'emergency_contact',
            )
        }),
        ('National Identity / Iqama', {
            'fields': (
                'iqama_number',
                'iqama_expiry_date',
            )
        }),
        ('Driving License', {
            'fields': (
                'license_number',
                'license_expiry_date',
                'license_type',
            )
        }),
        ('Vehicle Information', {
            'fields': (
                'vehicle_type',
                'vehicle_plate_number_arabic',
                'vehicle_plate_number_english',
                'vehicle_make',
                'vehicle_model',
                'vehicle_year',
                'vehicle_color',
                'vehicle_registration_number',
                'vehicle_registration_expiry_date',
            )
        }),
        ('Insurance Details', {
            'fields': (
                'insurance_provider',
                'insurance_policy_number',
                'insurance_expiry_date',
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


@admin.register(RiderDocument)
class RiderDocumentAdmin(admin.ModelAdmin):
    """Professional Rider Document Admin Interface"""
    
    list_display = [
        'rider_link',
        'document_type_badge',
        'is_verified_badge',
        'verified_by_link',
        'verified_at_formatted',
        'created_at_formatted',
    ]
    
    list_display_links = ['rider_link']
    
    list_filter = [
        'document_type',
        'is_verified',
        'verified_at',
        'created_at',
    ]
    
    search_fields = [
        'rider_profile__user__username',
        'rider_profile__user__email',
        'rider_profile__full_name',
        'rider_profile__iqama_number',
    ]
    
    raw_id_fields = ['rider_profile', 'verified_by']
    
    readonly_fields = [
        'created_at',
        'updated_at',
        'document_preview',
    ]
    
    fieldsets = (
        ('Rider Information', {
            'fields': ('rider_profile',)
        }),
        ('Document Information', {
            'fields': (
                'document_type',
                'document_image',
                'document_preview',
            )
        }),
        ('Verification', {
            'fields': (
                'is_verified',
                'verified_at',
                'verified_by',
                'notes',
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    list_per_page = 50
    
    actions = ['verify_documents', 'unverify_documents']
    
    def rider_link(self, obj):
        """Clickable rider link"""
        if obj.rider_profile and obj.rider_profile.pk:
            try:
                url = reverse('admin:riders_riderprofile_change', args=[obj.rider_profile.pk])
                name = obj.rider_profile.full_name or obj.rider_profile.user.username if obj.rider_profile.user else 'Unknown'
                return format_html('<a href="{}">{}</a>', url, name)
            except Exception:
                return obj.rider_profile.full_name or '-'
        return '-'
    rider_link.short_description = 'Rider'
    rider_link.admin_order_field = 'rider_profile__full_name'
    
    def document_type_badge(self, obj):
        """Display document type with badge"""
        colors = {
            'iqama_front': '#17a2b8',
            'iqama_back': '#17a2b8',
            'license_front': '#28a745',
            'license_back': '#28a745',
            'istimara_front': '#ffc107',
            'istimara_back': '#ffc107',
            'insurance': '#6c757d',
        }
        color = colors.get(obj.document_type, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 10px; border-radius: 4px; font-size: 11px;">{}</span>',
            color,
            obj.get_document_type_display()
        )
    document_type_badge.short_description = 'Document Type'
    document_type_badge.admin_order_field = 'document_type'
    
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
    
    def verified_by_link(self, obj):
        """Clickable verifier link"""
        if obj.verified_by and obj.verified_by.pk:
            try:
                url = reverse('admin:accounts_customuser_change', args=[obj.verified_by.pk])
                return format_html('<a href="{}">{}</a>', url, obj.verified_by.username or 'No username')
            except Exception:
                return obj.verified_by.username or '-'
        return format_html('<em style="color: #999;">Not verified</em>')
    verified_by_link.short_description = 'Verified By'
    verified_by_link.admin_order_field = 'verified_by__username'
    
    def verified_at_formatted(self, obj):
        """Format verified date"""
        if obj.verified_at:
            return obj.verified_at.strftime('%Y-%m-%d %H:%M')
        return format_html('<em style="color: #999;">Not verified</em>')
    verified_at_formatted.short_description = 'Verified At'
    verified_at_formatted.admin_order_field = 'verified_at'
    
    def created_at_formatted(self, obj):
        """Format creation date"""
        if obj.created_at:
            return obj.created_at.strftime('%Y-%m-%d %H:%M')
        return '-'
    created_at_formatted.short_description = 'Created'
    created_at_formatted.admin_order_field = 'created_at'
    
    def document_preview(self, obj):
        """Preview document image"""
        if obj.document_image:
            return format_html(
                '<img src="{}" style="max-width: 300px; max-height: 300px;" />',
                obj.document_image.url
            )
        return format_html('<em>No document uploaded</em>')
    document_preview.short_description = 'Preview'
    
    def verify_documents(self, request, queryset):
        """Bulk verify documents"""
        from django.utils import timezone
        updated = queryset.filter(is_verified=False).update(
            is_verified=True,
            verified_at=timezone.now(),
            verified_by=request.user
        )
        self.message_user(request, f'{updated} document(s) verified successfully.')
    verify_documents.short_description = "Verify selected documents"
    
    def unverify_documents(self, request, queryset):
        """Bulk unverify documents"""
        updated = queryset.filter(is_verified=True).update(
            is_verified=False,
            verified_at=None,
            verified_by=None
        )
        self.message_user(request, f'{updated} document(s) unverified.')
    unverify_documents.short_description = "Unverify selected documents"
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related(
            'rider_profile__user',
            'verified_by'
        )


@admin.register(TailorInvitationCode)
class TailorInvitationCodeAdmin(admin.ModelAdmin):
    """Admin interface for Tailor Invitation Codes"""
    
    list_display = ['code', 'tailor_name', 'is_active_badge', 'times_used', 'max_uses', 'expires_at_formatted', 'created_at_formatted']
    list_filter = ['is_active', 'created_at', 'expires_at']
    search_fields = ['code', 'tailor__username', 'tailor__tailor_profile__shop_name']
    readonly_fields = ['times_used', 'created_at', 'updated_at', 'created_by']
    raw_id_fields = ['tailor']
    
    fieldsets = (
        ('Code Information', {
            'fields': ('code', 'tailor', 'is_active')
        }),
        ('Usage Limits', {
            'fields': ('max_uses', 'times_used', 'expires_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    def tailor_name(self, obj):
        """Display tailor name"""
        if obj.tailor:
            if hasattr(obj.tailor, 'tailor_profile') and obj.tailor.tailor_profile:
                return obj.tailor.tailor_profile.shop_name or obj.tailor.username
            return obj.tailor.username
        return '-'
    tailor_name.short_description = 'Tailor'
    tailor_name.admin_order_field = 'tailor__username'
    
    def is_active_badge(self, obj):
        """Display active status"""
        if obj.is_active:
            can_use, msg = obj.can_be_used()
            if can_use:
                return format_html(
                    '<span style="background-color: #28a745; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">✓ Active</span>'
                )
            else:
                return format_html(
                    '<span style="background-color: #ffc107; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
                    msg
                )
        return format_html(
            '<span style="background-color: #dc3545; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">Inactive</span>'
        )
    is_active_badge.short_description = 'Status'
    
    def expires_at_formatted(self, obj):
        """Format expiration date"""
        if obj.expires_at:
            return obj.expires_at.strftime('%Y-%m-%d %H:%M')
        return format_html('<em style="color: #999;">Never</em>')
    expires_at_formatted.short_description = 'Expires'
    expires_at_formatted.admin_order_field = 'expires_at'
    
    def created_at_formatted(self, obj):
        """Format creation date"""
        if obj.created_at:
            return obj.created_at.strftime('%Y-%m-%d %H:%M')
        return '-'
    created_at_formatted.short_description = 'Created'
    created_at_formatted.admin_order_field = 'created_at'


@admin.register(TailorRiderAssociation)
class TailorRiderAssociationAdmin(admin.ModelAdmin):
    """Admin interface for Tailor-Rider Associations"""
    
    list_display = ['tailor_name', 'rider_name', 'is_active_badge', 'priority', 'joined_via_code', 'created_at_formatted']
    list_filter = ['is_active', 'created_at']
    search_fields = [
        'tailor__username', 
        'tailor__tailor_profile__shop_name',
        'rider__username',
        'rider__rider_profile__full_name'
    ]
    readonly_fields = ['created_at', 'updated_at', 'created_by']
    raw_id_fields = ['tailor', 'rider', 'joined_via_code']
    
    fieldsets = (
        ('Association', {
            'fields': ('tailor', 'rider', 'is_active')
        }),
        ('Details', {
            'fields': ('joined_via_code', 'nickname', 'priority')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    def tailor_name(self, obj):
        """Display tailor name"""
        if obj.tailor:
            if hasattr(obj.tailor, 'tailor_profile') and obj.tailor.tailor_profile:
                return obj.tailor.tailor_profile.shop_name or obj.tailor.username
            return obj.tailor.username
        return '-'
    tailor_name.short_description = 'Tailor'
    tailor_name.admin_order_field = 'tailor__username'
    
    def rider_name(self, obj):
        """Display rider name"""
        if obj.rider:
            if hasattr(obj.rider, 'rider_profile') and obj.rider.rider_profile:
                return obj.rider.rider_profile.full_name or obj.rider.username
            return obj.rider.username
        return '-'
    rider_name.short_description = 'Rider'
    rider_name.admin_order_field = 'rider__username'
    
    def is_active_badge(self, obj):
        """Display active status"""
        if obj.is_active:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">✓ Active</span>'
            )
        return format_html(
            '<span style="background-color: #dc3545; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">Inactive</span>'
        )
    is_active_badge.short_description = 'Status'
    is_active_badge.admin_order_field = 'is_active'
    
    def created_at_formatted(self, obj):
        """Format created date"""
        if obj.created_at:
            return obj.created_at.strftime('%Y-%m-%d %H:%M')
        return '-'
    created_at_formatted.short_description = 'Joined'
    created_at_formatted.admin_order_field = 'created_at'


