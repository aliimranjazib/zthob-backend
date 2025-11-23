from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.contrib import messages
from django.db.models import Count, Q
from .models import (
    TailorProfile, 
    FabricCategory, 
    Fabric, 
    FabricImage,
    FabricType,
    FabricTag,
    TailorProfileReview,
    ServiceArea
)


# ============================================================================
# INLINE ADMIN CLASSES
# ============================================================================

class FabricImageInline(admin.TabularInline):
    """Inline admin for FabricImages - shows images directly in Fabric detail view"""
    model = FabricImage
    extra = 1
    fields = ['image_preview', 'image', 'is_primary', 'order']
    readonly_fields = ['image_preview']
    can_delete = True
    show_change_link = True
    
    def image_preview(self, obj):
        """Display image preview thumbnail"""
        if obj and obj.pk and obj.image:
            try:
                return format_html(
                    '<img src="{}" width="80" height="80" style="border-radius: 5px; object-fit: cover; border: 2px solid #ddd;" />',
                    obj.image.url
                )
            except (ValueError, AttributeError):
                return format_html('<em style="color: #999;">Invalid image</em>')
        return format_html('<em style="color: #999;">No image</em>')
    image_preview.short_description = 'Preview'


# ============================================================================
# CUSTOM FILTERS
# ============================================================================

class ShopStatusFilter(admin.SimpleListFilter):
    """Custom filter for shop status"""
    title = 'Shop Status'
    parameter_name = 'shop_status_filter'
    
    def lookups(self, request, model_admin):
        return (
            ('open', 'Open'),
            ('closed', 'Closed'),
        )
    
    def queryset(self, request, queryset):
        if self.value() == 'open':
            return queryset.filter(shop_status=True)
        elif self.value() == 'closed':
            return queryset.filter(shop_status=False)


class StockStatusFilter(admin.SimpleListFilter):
    """Filter for fabric stock status"""
    title = 'Stock Status'
    parameter_name = 'stock_status'
    
    def lookups(self, request, model_admin):
        return (
            ('in_stock', 'In Stock'),
            ('low_stock', 'Low Stock (≤5)'),
            ('out_of_stock', 'Out of Stock'),
        )
    
    def queryset(self, request, queryset):
        if self.value() == 'in_stock':
            return queryset.filter(stock__gt=5)
        elif self.value() == 'low_stock':
            return queryset.filter(stock__lte=5, stock__gt=0)
        elif self.value() == 'out_of_stock':
            return queryset.filter(stock=0)


# ============================================================================
# TAILOR PROFILE ADMIN
# ============================================================================

@admin.register(TailorProfile)
class TailorProfileAdmin(admin.ModelAdmin):
    """
    Professional Tailor Profile Admin Interface
    """
    
    list_display = [
        'user_link',
        'shop_name',
        'contact_number',
        'experience_display',
        'shop_status_badge',
        'fabric_count',
        'revenue_display',
        'orders_count_display',
        'shop_image_preview',
        'created_at_formatted'
    ]
    
    list_display_links = ['shop_name']
    
    list_filter = [
        ShopStatusFilter,
        'shop_status',
        'establishment_year',
        'created_at',
    ]
    
    search_fields = [
        'user__username',
        'user__email',
        'shop_name',
        'contact_number',
        'address',
    ]
    
    raw_id_fields = ['user']
    
    readonly_fields = [
        'created_at',
        'updated_at',
        'shop_image_preview',
        'fabric_count_display',
        'analytics_summary',
    ]
    
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Business Information', {
            'fields': (
                'shop_name',
                'contact_number',
                'address',
            )
        }),
        ('Business Details', {
            'fields': (
                'establishment_year',
                'tailor_experience',
                'working_hours',
            ),
            'classes': ('collapse',)
        }),
        ('Shop Image', {
            'fields': ('shop_image', 'shop_image_preview')
        }),
        ('Status', {
            'fields': ('shop_status',)
        }),
        ('Statistics', {
            'fields': ('fabric_count_display',),
            'classes': ('collapse',)
        }),
        ('Analytics Summary', {
            'fields': ('analytics_summary',),
            'classes': ('collapse',),
            'description': 'Revenue and order statistics for this tailor'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    list_per_page = 50
    
    actions = ['activate_shops', 'deactivate_shops', 'export_profiles_csv']
    
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
    
    def experience_display(self, obj):
        """Display experience information"""
        if obj.tailor_experience:
            return format_html(
                '<strong>{} years</strong>',
                obj.tailor_experience
            )
        return format_html('<em style="color: #999;">Not set</em>')
    experience_display.short_description = 'Experience'
    experience_display.admin_order_field = 'tailor_experience'
    
    def shop_status_badge(self, obj):
        """Display shop status with badge"""
        if obj.shop_status:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 4px 10px; border-radius: 4px; font-size: 11px;">Open</span>'
            )
        return format_html(
            '<span style="background-color: #dc3545; color: white; padding: 4px 10px; border-radius: 4px; font-size: 11px;">Closed</span>'
        )
    shop_status_badge.short_description = 'Status'
    shop_status_badge.admin_order_field = 'shop_status'
    
    def fabric_count(self, obj):
        """Display fabric count with link"""
        count = obj.fabrics.count()
        if count > 0:
            url = reverse('admin:tailors_fabric_changelist')
            url += f'?tailor__id__exact={obj.pk}'
            return format_html('<a href="{}">{} fabric{}</a>', url, count, 's' if count != 1 else '')
        return '0'
    fabric_count.short_description = 'Fabrics'
    
    def revenue_display(self, obj):
        """Display total revenue from completed orders"""
        from apps.tailors.services import TailorAnalyticsService
        try:
            revenue = TailorAnalyticsService.calculate_total_revenue(obj.user)
            return format_html(
                '<strong style="color: #28a745;">${:,.2f}</strong>',
                float(revenue)
            )
        except Exception:
            return format_html('<em style="color: #999;">N/A</em>')
    revenue_display.short_description = 'Revenue'
    revenue_display.admin_order_field = 'user__tailor_orders__total_amount'
    
    def orders_count_display(self, obj):
        """Display completed orders count"""
        from apps.tailors.services import TailorAnalyticsService
        try:
            completed = TailorAnalyticsService.get_completed_orders_count(obj.user)
            total = TailorAnalyticsService.get_total_orders_count(obj.user)
            return format_html(
                '<span style="color: #17a2b8;">{}</span> / <span style="color: #6c757d;">{}</span>',
                completed,
                total
            )
        except Exception:
            return format_html('<em style="color: #999;">N/A</em>')
    orders_count_display.short_description = 'Orders (C/T)'
    
    def fabric_count_display(self, obj):
        """Display fabric count in detail view"""
        return obj.fabrics.count()
    fabric_count_display.short_description = 'Total Fabrics'
    
    def analytics_summary(self, obj):
        """Display analytics summary for the tailor"""
        from apps.tailors.services import TailorAnalyticsService
        
        try:
            analytics = TailorAnalyticsService.get_comprehensive_analytics(
                tailor_user=obj.user,
                days=30,
                weeks=12
            )
            
            return format_html(
                '<div style="padding: 15px; background: #f8f9fa; border-radius: 5px;">'
                '<h3 style="margin-top: 0; color: #333;">📊 Analytics Summary</h3>'
                '<div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin-top: 10px;">'
                '<div style="background: white; padding: 12px; border-radius: 5px; border-left: 4px solid #28a745;">'
                '<div style="font-size: 11px; color: #666; text-transform: uppercase;">Total Revenue</div>'
                '<div style="font-size: 20px; font-weight: bold; color: #28a745;">${}</div>'
                '</div>'
                '<div style="background: white; padding: 12px; border-radius: 5px; border-left: 4px solid #17a2b8;">'
                '<div style="font-size: 11px; color: #666; text-transform: uppercase;">Completed Orders</div>'
                '<div style="font-size: 20px; font-weight: bold; color: #17a2b8;">{}</div>'
                '</div>'
                '<div style="background: white; padding: 12px; border-radius: 5px; border-left: 4px solid #ffc107;">'
                '<div style="font-size: 11px; color: #666; text-transform: uppercase;">Total Orders</div>'
                '<div style="font-size: 20px; font-weight: bold; color: #ffc107;">{}</div>'
                '</div>'
                '<div style="background: white; padding: 12px; border-radius: 5px; border-left: 4px solid #6f42c1;">'
                '<div style="font-size: 11px; color: #666; text-transform: uppercase;">Completion Rate</div>'
                '<div style="font-size: 20px; font-weight: bold; color: #6f42c1;">{}%</div>'
                '</div>'
                '</div>'
                '<div style="margin-top: 15px; padding: 10px; background: white; border-radius: 5px;">'
                '<div style="font-size: 12px; color: #666;">📈 Last 30 Days Revenue: <strong>${:.2f}</strong></div>'
                '<div style="font-size: 12px; color: #666; margin-top: 5px;">📅 Analytics Generated: {}</div>'
                '</div>'
                '</div>',
                analytics['formatted_total_revenue'],
                analytics['completed_orders_count'],
                analytics['total_orders_count'],
                analytics['formatted_completion_percentage'],
                sum(float(day['earnings']) for day in analytics['daily_earnings']),
                analytics['analytics_period']['generated_at'][:19].replace('T', ' ')
            )
        except Exception as e:
            return format_html(
                '<div style="padding: 15px; background: #fff3cd; border-radius: 5px; color: #856404;">'
                '<strong>⚠️ Error loading analytics:</strong> {}'
                '</div>',
                str(e)
            )
    analytics_summary.short_description = 'Analytics Summary'
    analytics_summary.allow_tags = True
    
    def shop_image_preview(self, obj):
        """Display shop image preview"""
        if obj.shop_image:
            try:
                return format_html(
                    '<img src="{}" width="50" height="50" style="border-radius: 5px; object-fit: cover;" />',
                    obj.shop_image.url
                )
            except (ValueError, AttributeError):
                return format_html('<em style="color: #999;">Invalid image</em>')
        return format_html('<em style="color: #999;">No image</em>')
    shop_image_preview.short_description = 'Image'
    shop_image_preview.allow_tags = True
    
    def created_at_formatted(self, obj):
        """Format creation date"""
        return obj.created_at.strftime('%Y-%m-%d %H:%M')
    created_at_formatted.short_description = 'Created'
    created_at_formatted.admin_order_field = 'created_at'
    
    def activate_shops(self, request, queryset):
        """Bulk action to activate shops"""
        count = queryset.filter(shop_status=False).update(shop_status=True)
        self.message_user(
            request,
            f'Successfully activated {count} shop(s).',
            messages.SUCCESS
        )
    activate_shops.short_description = 'Activate selected shops'
    
    def deactivate_shops(self, request, queryset):
        """Bulk action to deactivate shops"""
        count = queryset.filter(shop_status=True).update(shop_status=False)
        self.message_user(
            request,
            f'Successfully deactivated {count} shop(s).',
            messages.SUCCESS
        )
    deactivate_shops.short_description = 'Deactivate selected shops'
    
    def export_profiles_csv(self, request, queryset):
        """Export tailor profiles to CSV"""
        import csv
        from django.http import HttpResponse
        from datetime import datetime
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="tailor_profiles_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'User',
            'Shop Name',
            'Contact Number',
            'Address',
            'Establishment Year',
            'Experience',
            'Shop Status',
            'Fabric Count',
            'Created At',
        ])
        
        for profile in queryset:
            writer.writerow([
                profile.user.username if profile.user else '',
                profile.shop_name or '',
                profile.contact_number or '',
                profile.address or '',
                profile.establishment_year or '',
                profile.tailor_experience or '',
                'Open' if profile.shop_status else 'Closed',
                profile.fabrics.count(),
                profile.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            ])
        
        return response
    export_profiles_csv.short_description = 'Export selected profiles to CSV'
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related('user').annotate(
            fabric_count=Count('fabrics')
        )


# ============================================================================
# FABRIC TYPE ADMIN
# ============================================================================

@admin.register(FabricType)
class FabricTypeAdmin(admin.ModelAdmin):
    """
    Professional Fabric Type Admin Interface
    """
    
    list_display = [
        'name',
        'slug',
        'fabric_count_badge',
        'created_at_formatted'
    ]
    
    list_filter = ['created_at']
    
    search_fields = ['name', 'slug']
    
    prepopulated_fields = {'slug': ('name',)}
    
    readonly_fields = ['created_at', 'updated_at']
    
    ordering = ['name']
    
    fieldsets = (
        ('Fabric Type Information', {
            'fields': ('name', 'slug'),
            'description': 'Basic fabric type information (e.g., Cotton, Silk, Wool)'
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
            'description': 'System timestamps'
        }),
    )
    
    list_per_page = 50
    
    def fabric_count_badge(self, obj):
        """Display fabric count with badge"""
        count = obj.fabrics.count()
        color = '#28a745' if count > 0 else '#6c757d'
        if count > 0:
            url = reverse('admin:tailors_fabric_changelist')
            url += f'?fabric_type__id__exact={obj.pk}'
            return format_html(
                '<a href="{}"><span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{} fabric{}</span></a>',
                url,
                color,
                count,
                's' if count != 1 else ''
            )
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">0 fabrics</span>',
            color
        )
    fabric_count_badge.short_description = 'Fabrics'
    fabric_count_badge.admin_order_field = 'fabrics__count'
    
    def created_at_formatted(self, obj):
        """Format creation date"""
        return obj.created_at.strftime('%Y-%m-%d')
    created_at_formatted.short_description = 'Created'
    created_at_formatted.admin_order_field = 'created_at'
    
    def get_queryset(self, request):
        """Optimize queries"""
        return super().get_queryset(request).annotate(
            fabric_count=Count('fabrics')
        )


# ============================================================================
# FABRIC CATEGORY ADMIN
# ============================================================================

@admin.register(FabricCategory)
class FabricCategoryAdmin(admin.ModelAdmin):
    """
    Professional Fabric Category Admin Interface
    """
    
    list_display = [
        'name',
        'slug',
        'is_active_badge',
        'fabric_count_badge',
        'created_at_formatted'
    ]
    
    list_filter = ['is_active', 'created_at']
    
    search_fields = ['name', 'slug']
    
    prepopulated_fields = {'slug': ('name',)}
    
    readonly_fields = ['created_at', 'updated_at']
    
    ordering = ['name']
    
    fieldsets = (
        ('Category Information', {
            'fields': ('name', 'slug', 'is_active'),
            'description': 'Fabric category information'
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
            'description': 'System timestamps'
        }),
    )
    
    list_per_page = 50
    
    actions = ['activate_categories', 'deactivate_categories']
    
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
    
    def fabric_count_badge(self, obj):
        """Display fabric count with badge"""
        count = obj.fabrics.count()
        color = '#28a745' if count > 0 else '#6c757d'
        if count > 0:
            url = reverse('admin:tailors_fabric_changelist')
            url += f'?category__id__exact={obj.pk}'
            return format_html(
                '<a href="{}"><span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{} fabric{}</span></a>',
                url,
                color,
                count,
                's' if count != 1 else ''
            )
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">0 fabrics</span>',
            color
        )
    fabric_count_badge.short_description = 'Fabrics'
    
    def created_at_formatted(self, obj):
        """Format creation date"""
        return obj.created_at.strftime('%Y-%m-%d')
    created_at_formatted.short_description = 'Created'
    created_at_formatted.admin_order_field = 'created_at'
    
    def activate_categories(self, request, queryset):
        """Bulk action to activate categories"""
        count = queryset.filter(is_active=False).update(is_active=True)
        self.message_user(
            request,
            f'Successfully activated {count} categor{("y" if count == 1 else "ies")}.',
            messages.SUCCESS
        )
    activate_categories.short_description = 'Activate selected categories'
    
    def deactivate_categories(self, request, queryset):
        """Bulk action to deactivate categories"""
        count = queryset.filter(is_active=True).update(is_active=False)
        self.message_user(
            request,
            f'Successfully deactivated {count} categor{("y" if count == 1 else "ies")}.',
            messages.SUCCESS
        )
    deactivate_categories.short_description = 'Deactivate selected categories'
    
    def get_queryset(self, request):
        """Optimize queries"""
        return super().get_queryset(request).annotate(
            fabric_count=Count('fabrics')
        )


# ============================================================================
# FABRIC TAG ADMIN
# ============================================================================

@admin.register(FabricTag)
class FabricTagAdmin(admin.ModelAdmin):
    """
    Professional Fabric Tag Admin Interface
    """
    
    list_display = [
        'name',
        'slug',
        'is_active_badge',
        'fabric_count_badge',
        'created_at_formatted'
    ]
    
    list_filter = ['is_active', 'created_at']
    
    search_fields = ['name', 'slug']
    
    prepopulated_fields = {'slug': ('name',)}
    
    readonly_fields = ['created_at', 'updated_at']
    
    ordering = ['name']
    
    fieldsets = (
        ('Tag Information', {
            'fields': ('name', 'slug', 'is_active'),
            'description': 'Fabric tag information for categorization'
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
            'description': 'System timestamps'
        }),
    )
    
    list_per_page = 50
    
    actions = ['activate_tags', 'deactivate_tags']
    
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
    
    def fabric_count_badge(self, obj):
        """Display fabric count with badge"""
        count = obj.fabrics.count()
        color = '#28a745' if count > 0 else '#6c757d'
        if count > 0:
            url = reverse('admin:tailors_fabric_changelist')
            url += f'?tags__id__exact={obj.pk}'
            return format_html(
                '<a href="{}"><span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{} fabric{}</span></a>',
                url,
                color,
                count,
                's' if count != 1 else ''
            )
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">0 fabrics</span>',
            color
        )
    fabric_count_badge.short_description = 'Fabrics'
    
    def created_at_formatted(self, obj):
        """Format creation date"""
        return obj.created_at.strftime('%Y-%m-%d')
    created_at_formatted.short_description = 'Created'
    created_at_formatted.admin_order_field = 'created_at'
    
    def activate_tags(self, request, queryset):
        """Bulk action to activate tags"""
        count = queryset.filter(is_active=False).update(is_active=True)
        self.message_user(
            request,
            f'Successfully activated {count} tag(s).',
            messages.SUCCESS
        )
    activate_tags.short_description = 'Activate selected tags'
    
    def deactivate_tags(self, request, queryset):
        """Bulk action to deactivate tags"""
        count = queryset.filter(is_active=True).update(is_active=False)
        self.message_user(
            request,
            f'Successfully deactivated {count} tag(s).',
            messages.SUCCESS
        )
    deactivate_tags.short_description = 'Deactivate selected tags'
    
    def get_queryset(self, request):
        """Optimize queries"""
        return super().get_queryset(request).annotate(
            fabric_count=Count('fabrics')
        )


# ============================================================================
# FABRIC ADMIN
# ============================================================================

@admin.register(Fabric)
class FabricAdmin(admin.ModelAdmin):
    """
    Professional Fabric Admin Interface
    """
    
    list_display = [
        'name',
        'sku',
        'tailor_link',
        'category',
        'fabric_type',
        'price_formatted',
        'stock_badge',
        'season_badge',
        'is_active_badge',
        'image_count',
        'created_at_formatted'
    ]
    
    list_display_links = ['name']
    
    list_filter = [
        StockStatusFilter,
        'category',
        'fabric_type',
        'is_active',
        'seasons',
        'created_at',
    ]
    
    search_fields = [
        'name',
        'sku',
        'description',
        'tailor__shop_name',
        'tailor__user__username',
        'fabric_type__name',
    ]
    
    autocomplete_fields = ['tailor', 'category', 'fabric_type']  # Use autocomplete dropdowns for better UX
    
    readonly_fields = [
        'sku',
        'created_at',
        'updated_at',
        'created_by',
        'image_count_display',
        'image_gallery_display',
    ]
    
    inlines = [FabricImageInline]
    
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'name',
                'description',
                'sku',
            )
        }),
        ('Categorization', {
            'fields': (
                'category',
                'fabric_type',
                'tailor',
            )
        }),
        ('Attributes', {
            'fields': (
                'seasons',
                'tags',
            )
        }),
        ('Pricing & Stock', {
            'fields': (
                'price',
                'stock',
                'is_active',
            )
        }),
        ('Legacy Image', {
            'fields': ('fabric_image',),
            'classes': ('collapse',),
            'description': 'Legacy single image field - use gallery images instead'
        }),
        ('Fabric Images', {
            'fields': ('image_gallery_display',),
            'description': 'Manage fabric images using the inline section below. Images are displayed here for quick reference.',
        }),
        ('Statistics', {
            'fields': ('image_count_display',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    list_per_page = 50
    
    actions = [
        'activate_fabrics',
        'deactivate_fabrics',
        'mark_as_low_stock',
        'export_fabrics_csv',
    ]
    
    def tailor_link(self, obj):
        """Clickable tailor link"""
        if obj.tailor and obj.tailor.pk:
            try:
                url = reverse('admin:tailors_tailorprofile_change', args=[obj.tailor.pk])
                if obj.tailor.user:
                    shop_name = obj.tailor.shop_name or obj.tailor.user.username or 'Unknown'
                else:
                    shop_name = obj.tailor.shop_name or 'Unknown'
                return format_html('<a href="{}">{}</a>', url, shop_name)
            except Exception:
                shop_name = obj.tailor.shop_name or (obj.tailor.user.username if obj.tailor.user else 'Unknown')
                return shop_name
        return '-'
    tailor_link.short_description = 'Tailor'
    tailor_link.admin_order_field = 'tailor__shop_name'
    
    def price_formatted(self, obj):
        """Format price"""
        try:
            price = float(obj.price) if obj.price is not None else 0.0
            return format_html(
                '<strong style="color: #28a745;">${:,.2f}</strong>',
                price
            )
        except (ValueError, TypeError):
            return format_html('<em style="color: #999;">N/A</em>')
    price_formatted.short_description = 'Price'
    price_formatted.admin_order_field = 'price'
    
    def stock_badge(self, obj):
        """Display stock with color-coded badge"""
        if obj.stock == 0:
            color = '#dc3545'
            text = 'Out of Stock'
        elif obj.stock <= 5:
            color = '#ffc107'
            text = f'Low ({obj.stock})'
        else:
            color = '#28a745'
            text = f'In Stock ({obj.stock})'
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 10px; border-radius: 4px; font-size: 11px;">{}</span>',
            color,
            text
        )
    stock_badge.short_description = 'Stock'
    stock_badge.admin_order_field = 'stock'
    
    def season_badge(self, obj):
        """Display season with badge"""
        colors = {
            'summer': '#ffc107',
            'winter': '#17a2b8',
            'all_season': '#28a745',
        }
        color = colors.get(obj.seasons, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.get_seasons_display()
        )
    season_badge.short_description = 'Season'
    season_badge.admin_order_field = 'seasons'
    
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
    
    def image_count(self, obj):
        """Display image count"""
        count = obj.gallery.count()
        if count > 0:
            url = reverse('admin:tailors_fabricimage_changelist')
            url += f'?fabric__id__exact={obj.pk}'
            return format_html('<a href="{}">{} image{}</a>', url, count, 's' if count != 1 else '')
        return '0'
    image_count.short_description = 'Images'
    
    def image_count_display(self, obj):
        """Display image count in detail view"""
        return obj.gallery.count()
    image_count_display.short_description = 'Total Images'
    
    def image_gallery_display(self, obj):
        """Display all fabric images in a gallery view"""
        if not obj or not obj.pk:
            return format_html('<p style="color: #999;">Save the fabric first to manage images.</p>')
        
        images = obj.gallery.all().order_by('order', 'id')
        if not images:
            return format_html('<p style="color: #999;">No images uploaded yet. Add images using the "Fabric Images" section below.</p>')
        
        html_parts = ['<div style="display: flex; flex-wrap: wrap; gap: 15px; margin-top: 10px;">']
        for img in images:
            try:
                primary_badge = ''
                if img.is_primary:
                    primary_badge = '<span style="position: absolute; top: 5px; right: 5px; background: #28a745; color: white; padding: 2px 8px; border-radius: 3px; font-size: 10px;">PRIMARY</span>'
                
                html_parts.append(format_html(
                    '<div style="position: relative; border: 2px solid {}; border-radius: 8px; padding: 5px; background: white;">'
                    '<img src="{}" width="150" height="150" style="border-radius: 5px; object-fit: cover; display: block;" />'
                    '{}'
                    '<div style="text-align: center; margin-top: 5px; font-size: 11px; color: #666;">Order: {}</div>'
                    '</div>',
                    '#28a745' if img.is_primary else '#ddd',
                    img.image.url,
                    primary_badge,
                    img.order
                ))
            except (ValueError, AttributeError):
                continue
        
        html_parts.append('</div>')
        html_parts.append('<p style="margin-top: 15px; color: #666; font-size: 12px;"><strong>Note:</strong> Use the "Fabric Images" section below to add, edit, or delete images.</p>')
        return format_html(''.join(html_parts))
    image_gallery_display.short_description = 'Image Gallery'
    
    def created_at_formatted(self, obj):
        """Format creation date"""
        return obj.created_at.strftime('%Y-%m-%d %H:%M')
    created_at_formatted.short_description = 'Created'
    created_at_formatted.admin_order_field = 'created_at'
    
    def activate_fabrics(self, request, queryset):
        """Bulk action to activate fabrics"""
        count = queryset.filter(is_active=False).update(is_active=True)
        self.message_user(
            request,
            f'Successfully activated {count} fabric(s).',
            messages.SUCCESS
        )
    activate_fabrics.short_description = 'Activate selected fabrics'
    
    def deactivate_fabrics(self, request, queryset):
        """Bulk action to deactivate fabrics"""
        count = queryset.filter(is_active=True).update(is_active=False)
        self.message_user(
            request,
            f'Successfully deactivated {count} fabric(s).',
            messages.SUCCESS
        )
    deactivate_fabrics.short_description = 'Deactivate selected fabrics'
    
    def mark_as_low_stock(self, request, queryset):
        """Mark fabrics as low stock (set stock to 5)"""
        count = queryset.update(stock=5)
        self.message_user(
            request,
            f'Successfully marked {count} fabric(s) as low stock.',
            messages.SUCCESS
        )
    mark_as_low_stock.short_description = 'Mark selected fabrics as low stock'
    
    def export_fabrics_csv(self, request, queryset):
        """Export fabrics to CSV"""
        import csv
        from django.http import HttpResponse
        from datetime import datetime
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="fabrics_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'SKU',
            'Name',
            'Tailor',
            'Category',
            'Fabric Type',
            'Price',
            'Stock',
            'Season',
            'Is Active',
            'Created At',
        ])
        
        for fabric in queryset:
            writer.writerow([
                fabric.sku,
                fabric.name,
                fabric.tailor.shop_name if fabric.tailor else '',
                fabric.category.name if fabric.category else '',
                fabric.fabric_type.name if fabric.fabric_type else '',
                fabric.price,
                fabric.stock,
                fabric.get_seasons_display(),
                'Yes' if fabric.is_active else 'No',
                fabric.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            ])
        
        return response
    export_fabrics_csv.short_description = 'Export selected fabrics to CSV'
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related(
            'tailor',
            'tailor__user',
            'category',
            'fabric_type',
            'created_by'
        ).prefetch_related('tags', 'gallery').annotate(
            image_count=Count('gallery')
        )


# ============================================================================
# FABRIC IMAGE ADMIN
# ============================================================================

@admin.register(FabricImage)
class FabricImageAdmin(admin.ModelAdmin):
    """
    Professional Fabric Image Admin Interface
    """
    
    list_display = [
        'fabric_link',
        'image_preview',
        'is_primary_badge',
        'order',
        'created_at_formatted'
    ]
    
    list_display_links = ['fabric_link']
    
    list_filter = [
        'is_primary',
        'created_at',
    ]
    
    search_fields = [
        'fabric__name',
        'fabric__sku',
    ]
    
    raw_id_fields = ['fabric']
    
    readonly_fields = [
        'created_at',
        'image_preview_detail',
    ]
    
    fieldsets = (
        ('Fabric Information', {
            'fields': ('fabric',)
        }),
        ('Image', {
            'fields': ('image', 'image_preview_detail')
        }),
        ('Settings', {
            'fields': (
                'is_primary',
                'order',
            )
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    list_per_page = 50
    
    actions = ['set_as_primary', 'export_images_csv']
    
    def fabric_link(self, obj):
        """Clickable fabric link"""
        if obj.fabric and obj.fabric.pk:
            try:
                url = reverse('admin:tailors_fabric_change', args=[obj.fabric.pk])
                return format_html('<a href="{}">{}</a>', url, obj.fabric.name or 'No name')
            except Exception:
                return obj.fabric.name or '-'
        return '-'
    fabric_link.short_description = 'Fabric'
    fabric_link.admin_order_field = 'fabric__name'
    
    def image_preview(self, obj):
        """Display image preview in list"""
        if obj.image:
            try:
                return format_html(
                    '<img src="{}" width="50" height="50" style="border-radius: 5px; object-fit: cover;" />',
                    obj.image.url
                )
            except (ValueError, AttributeError):
                return format_html('<em style="color: #999;">Invalid image</em>')
        return format_html('<em style="color: #999;">No image</em>')
    image_preview.short_description = 'Preview'
    image_preview.allow_tags = True
    
    def image_preview_detail(self, obj):
        """Display larger image preview in detail view"""
        if obj.image:
            try:
                return format_html(
                    '<img src="{}" width="200" height="200" style="border-radius: 5px; object-fit: cover;" />',
                    obj.image.url
                )
            except (ValueError, AttributeError):
                return format_html('<em style="color: #999;">Invalid image</em>')
        return format_html('<em style="color: #999;">No image</em>')
    image_preview_detail.short_description = 'Image Preview'
    image_preview_detail.allow_tags = True
    
    def is_primary_badge(self, obj):
        """Display primary status"""
        if obj.is_primary:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 4px 10px; border-radius: 4px; font-size: 11px;">Primary</span>'
            )
        return '-'
    is_primary_badge.short_description = 'Primary'
    is_primary_badge.admin_order_field = 'is_primary'
    
    def created_at_formatted(self, obj):
        """Format creation date"""
        return obj.created_at.strftime('%Y-%m-%d %H:%M')
    created_at_formatted.short_description = 'Created'
    created_at_formatted.admin_order_field = 'created_at'
    
    def set_as_primary(self, request, queryset):
        """Set selected images as primary"""
        count = 0
        for image in queryset:
            # Unset other primary images for this fabric
            FabricImage.objects.filter(
                fabric=image.fabric,
                is_primary=True
            ).exclude(pk=image.pk).update(is_primary=False)
            image.is_primary = True
            image.save()
            count += 1
        self.message_user(
            request,
            f'Successfully set {count} image(s) as primary.',
            messages.SUCCESS
        )
    set_as_primary.short_description = 'Set selected images as primary'
    
    def export_images_csv(self, request, queryset):
        """Export image information to CSV"""
        import csv
        from django.http import HttpResponse
        from datetime import datetime
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="fabric_images_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Fabric',
            'Fabric SKU',
            'Image URL',
            'Is Primary',
            'Order',
            'Created At',
        ])
        
        for image in queryset:
            writer.writerow([
                image.fabric.name if image.fabric else '',
                image.fabric.sku if image.fabric else '',
                image.image.url if (image.image and hasattr(image.image, 'url')) else '',
                'Yes' if image.is_primary else 'No',
                image.order,
                image.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            ])
        
        return response
    export_images_csv.short_description = 'Export selected images to CSV'
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related('fabric')


# ============================================================================
# TAILOR PROFILE REVIEW ADMIN
# ============================================================================

@admin.register(TailorProfileReview)
class TailorProfileReviewAdmin(admin.ModelAdmin):
    """
    Professional Tailor Profile Review Admin Interface
    """
    
    list_display = [
        'shop_name_link',
        'user_email',
        'user_name',
        'review_status_badge',
        'submitted_at_formatted',
        'reviewed_at_formatted',
        'reviewed_by_link'
    ]
    
    list_display_links = ['shop_name_link']
    
    list_filter = [
        'review_status',
        'submitted_at',
        'reviewed_at',
    ]
    
    search_fields = [
        'profile__shop_name',
        'profile__user__email',
        'profile__user__username',
        'rejection_reason',
    ]
    
    raw_id_fields = ['profile', 'reviewed_by']
    
    readonly_fields = [
        'created_at',
        'updated_at',
        'submitted_at',
        'reviewed_at',
        'reviewed_by',
    ]
    
    date_hierarchy = 'submitted_at'
    
    fieldsets = (
        ('Profile Information', {
            'fields': ('profile',),
            'description': 'Basic profile information of the tailor'
        }),
        ('Review Status', {
            'fields': (
                'review_status',
                'submitted_at',
                'reviewed_at',
                'reviewed_by',
            ),
            'description': 'Current review status and timeline'
        }),
        ('Review Details', {
            'fields': (
                'rejection_reason',
                'service_areas',
            ),
            'description': 'Rejection reason (if rejected) and service areas'
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
            'description': 'System timestamps'
        }),
    )
    
    list_per_page = 50
    
    # Ensure actions are visible
    actions_on_top = True
    actions_on_bottom = True
    
    actions = [
        'approve_profiles',
        'reject_profiles',
        'export_reviews_csv',
    ]
    
    def shop_name_link(self, obj):
        """Clickable shop name"""
        if obj.profile and obj.profile.pk:
            try:
                url = reverse('admin:tailors_tailorprofile_change', args=[obj.profile.pk])
                shop_name = obj.profile.shop_name or 'No Shop Name'
                return format_html('<a href="{}"><strong>{}</strong></a>', url, shop_name)
            except Exception:
                return obj.profile.shop_name or 'No Shop Name'
        return '-'
    shop_name_link.short_description = 'Shop Name'
    shop_name_link.admin_order_field = 'profile__shop_name'
    
    def user_email(self, obj):
        """Display user email"""
        if obj.profile and obj.profile.user:
            return obj.profile.user.email
        return '-'
    user_email.short_description = 'Email'
    user_email.admin_order_field = 'profile__user__email'
    
    def user_name(self, obj):
        """Display user name"""
        if obj.profile and obj.profile.user:
            full_name = obj.profile.user.get_full_name()
            return full_name or obj.profile.user.username
        return '-'
    user_name.short_description = 'Owner Name'
    user_name.admin_order_field = 'profile__user__first_name'
    
    def review_status_badge(self, obj):
        """Display review status with color-coded badge"""
        colors = {
            'draft': '#6c757d',
            'pending': '#ffc107',
            'approved': '#28a745',
            'rejected': '#dc3545',
        }
        color = colors.get(obj.review_status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 10px; border-radius: 4px; font-weight: 500; font-size: 11px;">{}</span>',
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
                return obj.reviewed_by.username or 'Unknown'
        return format_html('<em style="color: #999;">Not reviewed</em>')
    reviewed_by_link.short_description = 'Reviewed By'
    reviewed_by_link.admin_order_field = 'reviewed_by__username'
    
    def approve_profiles(self, request, queryset):
        """Approve selected profiles"""
        from django.utils import timezone
        count = queryset.filter(review_status='pending').update(
            review_status='approved',
            reviewed_at=timezone.now(),
            reviewed_by=request.user,
            rejection_reason=''
        )
        self.message_user(
            request,
            f'{count} profile(s) approved successfully.',
            messages.SUCCESS
        )
    approve_profiles.short_description = "✅ Approve selected profiles"
    approve_profiles.allowed_permissions = ('change',)
    
    def reject_profiles(self, request, queryset):
        """Reject selected profiles"""
        from django.utils import timezone
        count = queryset.filter(review_status='pending').update(
            review_status='rejected',
            reviewed_at=timezone.now(),
            reviewed_by=request.user
        )
        self.message_user(
            request,
            f'{count} profile(s) rejected. Please add rejection reasons manually.',
            messages.SUCCESS
        )
    reject_profiles.short_description = "❌ Reject selected profiles"
    reject_profiles.allowed_permissions = ('change',)
    
    def export_reviews_csv(self, request, queryset):
        """Export reviews to CSV"""
        import csv
        from django.http import HttpResponse
        from datetime import datetime
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="tailor_reviews_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Shop Name',
            'User Email',
            'User Name',
            'Review Status',
            'Submitted At',
            'Reviewed At',
            'Reviewed By',
            'Rejection Reason',
        ])
        
        for review in queryset:
            writer.writerow([
                review.profile.shop_name if review.profile else '',
                review.profile.user.email if review.profile and review.profile.user else '',
                review.profile.user.get_full_name() if review.profile and review.profile.user else '',
                review.get_review_status_display(),
                review.submitted_at.strftime('%Y-%m-%d %H:%M:%S') if review.submitted_at else '',
                review.reviewed_at.strftime('%Y-%m-%d %H:%M:%S') if review.reviewed_at else '',
                review.reviewed_by.username if review.reviewed_by else '',
                review.rejection_reason or '',
            ])
        
        return response
    export_reviews_csv.short_description = '📥 Export selected reviews to CSV'
    export_reviews_csv.allowed_permissions = ('view',)
    
    def get_queryset(self, request):
        """Optimize queries"""
        return super().get_queryset(request).select_related(
            'profile__user',
            'reviewed_by'
        )
    
    def get_readonly_fields(self, request, obj=None):
        """Make fields readonly based on review status"""
        readonly_fields = list(self.readonly_fields)
        
        if obj and obj.review_status in ['approved', 'rejected']:
            readonly_fields.append('review_status')
            
        return readonly_fields
    
    def save_model(self, request, obj, form, change):
        """Custom save to handle review status changes"""
        from django.utils import timezone
        
        if change and 'review_status' in form.changed_data:
            if obj.review_status in ['approved', 'rejected']:
                obj.reviewed_at = timezone.now()
                obj.reviewed_by = request.user
                
                if obj.review_status == 'approved':
                    obj.rejection_reason = ''
                    
        super().save_model(request, obj, form, change)
    

# ============================================================================
# SERVICE AREA ADMIN
# ============================================================================

@admin.register(ServiceArea)
class ServiceAreaAdmin(admin.ModelAdmin):
    """
    Professional Service Area Admin Interface
    """
    
    list_display = [
        'name',
        'city',
        'is_active_badge',
        'created_at_formatted'
    ]
    
    list_filter = [
        'city',
        'is_active',
        'created_at',
    ]
    
    search_fields = [
        'name',
        'city',
    ]
    
    readonly_fields = [
        'created_at',
        'updated_at',
    ]
    
    fieldsets = (
        ('Area Information', {
            'fields': ('name', 'city', 'is_active'),
            'description': 'Basic service area information'
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
            'description': 'System timestamps'
        }),
    )
    
    list_per_page = 50
    
    actions = ['activate_areas', 'deactivate_areas']
    
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
        return obj.created_at.strftime('%Y-%m-%d')
    created_at_formatted.short_description = 'Created'
    created_at_formatted.admin_order_field = 'created_at'
    
    def activate_areas(self, request, queryset):
        """Bulk action to activate service areas"""
        count = queryset.filter(is_active=False).update(is_active=True)
        self.message_user(
            request,
            f'Successfully activated {count} service area(s).',
            messages.SUCCESS
        )
    activate_areas.short_description = 'Activate selected service areas'
    
    def deactivate_areas(self, request, queryset):
        """Bulk action to deactivate service areas"""
        count = queryset.filter(is_active=True).update(is_active=False)
        self.message_user(
            request,
            f'Successfully deactivated {count} service area(s).',
            messages.SUCCESS
        )
    deactivate_areas.short_description = 'Deactivate selected service areas'
    
    def get_queryset(self, request):
        """Optimize queries"""
        return super().get_queryset(request)
