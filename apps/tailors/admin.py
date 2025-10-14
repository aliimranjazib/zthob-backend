from django.contrib import admin
from .models import (
    TailorProfile, 
    FabricCategory, 
    Fabric, 
    FabricImage,
    FabricType,
    FabricTag,
    TailorProfileReview,
    ServiceArea,
    TailorServiceArea
)
# Register your models here.
@admin.register(TailorProfile)
class TailorProfileAdmin(admin.ModelAdmin):
    # Essential tailor info
    list_display = ['user', 'shop_name', 'contact_number', 'shop_status', 'get_shop_image_preview']
    list_filter = ['shop_status']
    search_fields = ['user__username', 'shop_name', 'contact_number']
    raw_id_fields = ['user']
    readonly_fields = ['created_at', 'updated_at', 'get_shop_image_preview']
    
    # Custom display method
    def get_shop_image_preview(self, obj):
        """Display shop image preview in admin list."""
        if obj.shop_image:
            return f'<img src="{obj.shop_image.url}" width="50" height="50" style="border-radius: 5px;" />'
        return "No Image"
    get_shop_image_preview.short_description = 'Shop Image'
    get_shop_image_preview.allow_tags = True
    
    # Grouped fields
    fieldsets = (
        ('Basic Info', {'fields': ('user', 'shop_name', 'contact_number')}),
        ('Business Details', {'fields': ('establishment_year', 'tailor_experience', 'working_hours')}),
        ('Location', {'fields': ('address',)}),
        ('Shop Image', {'fields': ('shop_image', 'get_shop_image_preview')}),
        ('Status', {'fields': ('shop_status',)}),
    )

@admin.register(FabricType)
class FabricTypeAdmin(admin.ModelAdmin):
    # Fabric type management
    list_display = ['name', 'slug', 'get_fabric_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['name']
    
    # Custom display methods
    def get_fabric_count(self, obj):
        """Display count of fabrics using this type."""
        return obj.fabrics.count()
    get_fabric_count.short_description = 'Fabrics Count'
    get_fabric_count.admin_order_field = 'fabrics__count'
    
    # Grouped form
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
    
    def get_queryset(self, request):
        """Optimize queries by prefetching related objects."""
        return super().get_queryset(request).prefetch_related('fabrics')

@admin.register(FabricCategory)
class FabricCategoryAdmin(admin.ModelAdmin):
    # Simple category management
    list_display = ['name', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at']
    
    # Simple form
    fieldsets = (
        ('Category Info', {'fields': ('name', 'slug', 'is_active')}),
    )

@admin.register(FabricTag)
class FabricTagAdmin(admin.ModelAdmin):
    # Fabric tag management
    list_display = ['name', 'slug', 'is_active', 'get_fabric_count', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['name']
    
    # Custom display methods
    def get_fabric_count(self, obj):
        """Display count of fabrics using this tag."""
        return obj.fabrics.count()
    get_fabric_count.short_description = 'Fabrics Count'
    get_fabric_count.admin_order_field = 'fabrics__count'
    
    # Grouped form
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
    
    def get_queryset(self, request):
        """Optimize queries by prefetching related objects."""
        return super().get_queryset(request).prefetch_related('fabrics')

@admin.register(Fabric)
class FabricAdmin(admin.ModelAdmin):
    # Essential fabric info
    list_display = ['name', 'tailor', 'category', 'fabric_type', 'price', 'stock', 'is_active']
    list_filter = ['category', 'fabric_type', 'is_active', 'seasons']
    search_fields = ['name', 'sku', 'tailor__shop_name', 'fabric_type__name']
    raw_id_fields = ['tailor', 'category', 'fabric_type']
    readonly_fields = ['sku', 'created_at', 'updated_at']
    
    # Grouped fabric form
    fieldsets = (
        ('Basic Info', {'fields': ('name', 'description', 'category', 'fabric_type', 'tailor')}),
        ('Attributes', {'fields': ('seasons', 'tags')}),
        ('Pricing & Stock', {'fields': ('price', 'stock', 'is_active')}),
        ('Images', {'fields': ('fabric_image',)}),
    )

@admin.register(FabricImage)
class FabricImageAdmin(admin.ModelAdmin):
    # Simple image management
    list_display = ['fabric', 'is_primary', 'order']
    list_filter = ['is_primary']
    search_fields = ['fabric__name']
    raw_id_fields = ['fabric']
    readonly_fields = ['created_at']
    
    # Simple image form
    fieldsets = (
        ('Image Info', {'fields': ('fabric', 'image', 'is_primary', 'order')}),
    )

@admin.register(TailorProfileReview)
class TailorProfileReviewAdmin(admin.ModelAdmin):
    # Review management
    list_display = [
        'get_shop_name', 'get_user_email', 'get_user_name', 
        'review_status', 'submitted_at', 'reviewed_at', 'get_reviewed_by'
    ]
    list_filter = ['review_status', 'submitted_at', 'reviewed_at']
    search_fields = ['profile__shop_name', 'profile__user__email', 'profile__user__username']
    raw_id_fields = ['profile', 'reviewed_by']
    readonly_fields = ['created_at', 'updated_at', 'submitted_at', 'reviewed_at', 'reviewed_by']
    actions = ['approve_profiles', 'reject_profiles']
    
    # Custom display methods
    def get_shop_name(self, obj):
        return obj.profile.shop_name or 'No Shop Name'
    get_shop_name.short_description = 'Shop Name'
    get_shop_name.admin_order_field = 'profile__shop_name'
    
    def get_user_email(self, obj):
        return obj.profile.user.email
    get_user_email.short_description = 'Email'
    get_user_email.admin_order_field = 'profile__user__email'
    
    def get_user_name(self, obj):
        return obj.profile.user.get_full_name() or obj.profile.user.username
    get_user_name.short_description = 'Owner Name'
    get_user_name.admin_order_field = 'profile__user__first_name'
    
    def get_reviewed_by(self, obj):
        return obj.reviewed_by.get_full_name() if obj.reviewed_by else 'Not Reviewed'
    get_reviewed_by.short_description = 'Reviewed By'
    get_reviewed_by.admin_order_field = 'reviewed_by__first_name'
    
    # Custom actions
    def approve_profiles(self, request, queryset):
        """Approve selected profiles."""
        from django.utils import timezone
        updated = queryset.filter(review_status='pending').update(
            review_status='approved',
            reviewed_at=timezone.now(),
            reviewed_by=request.user,
            rejection_reason=''
        )
        self.message_user(request, f'{updated} profile(s) approved successfully.')
    approve_profiles.short_description = "Approve selected profiles"
    
    def reject_profiles(self, request, queryset):
        """Reject selected profiles."""
        from django.utils import timezone
        updated = queryset.filter(review_status='pending').update(
            review_status='rejected',
            reviewed_at=timezone.now(),
            reviewed_by=request.user
        )
        self.message_user(request, f'{updated} profile(s) rejected. Please add rejection reasons manually.')
    reject_profiles.short_description = "Reject selected profiles"
    
    # Grouped review form
    fieldsets = (
        ('Profile Information', {
            'fields': ('profile',),
            'description': 'Basic profile information of the tailor'
        }),
        ('Review Status', {
            'fields': ('review_status', 'submitted_at', 'reviewed_at', 'reviewed_by'),
            'description': 'Current review status and timeline'
        }),
        ('Review Details', {
            'fields': ('rejection_reason', 'service_areas'),
            'description': 'Rejection reason (if rejected) and service areas'
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
            'description': 'System timestamps'
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queries by selecting related objects."""
        return super().get_queryset(request).select_related(
            'profile__user', 'reviewed_by'
        )
    
    def get_readonly_fields(self, request, obj=None):
        """Make fields readonly based on review status."""
        readonly_fields = list(self.readonly_fields)
        
        if obj and obj.review_status in ['approved', 'rejected']:
            # If already reviewed, make review_status readonly
            readonly_fields.append('review_status')
            
        return readonly_fields
    
    def save_model(self, request, obj, form, change):
        """Custom save to handle review status changes."""
        from django.utils import timezone
        
        if change and 'review_status' in form.changed_data:
            # If review status is being changed
            if obj.review_status in ['approved', 'rejected']:
                obj.reviewed_at = timezone.now()
                obj.reviewed_by = request.user
                
                if obj.review_status == 'approved':
                    obj.rejection_reason = ''
                    
        super().save_model(request, obj, form, change)
    
    class Media:
        css = {
            'all': ('admin/css/tailor_review_admin.css',)
        }
        js = ('admin/js/tailor_review_admin.js',)

@admin.register(ServiceArea)
class ServiceAreaAdmin(admin.ModelAdmin):
    # Service area management
    list_display = ['name', 'city', 'is_active', 'get_tailor_count']
    list_filter = ['city', 'is_active']
    search_fields = ['name', 'city']
    readonly_fields = ['created_at', 'updated_at']
    
    # Custom display methods
    def get_tailor_count(self, obj):
        return obj.tailors.count()
    get_tailor_count.short_description = 'Tailors Count'
    get_tailor_count.admin_order_field = 'tailors__count'
    
    # Grouped form
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
    
    def get_queryset(self, request):
        """Optimize queries by prefetching related objects."""
        return super().get_queryset(request).prefetch_related('tailors')

@admin.register(TailorServiceArea)
class TailorServiceAreaAdmin(admin.ModelAdmin):
    # Tailor service area management
    list_display = ['get_tailor_name', 'get_service_area', 'is_primary', 'delivery_fee', 'estimated_delivery_days']
    list_filter = ['is_primary', 'service_area__city', 'service_area__is_active']
    search_fields = ['tailor__shop_name', 'tailor__user__email', 'service_area__name']
    raw_id_fields = ['tailor', 'service_area']
    readonly_fields = ['created_at', 'updated_at']
    
    # Custom display methods
    def get_tailor_name(self, obj):
        return obj.tailor.shop_name or obj.tailor.user.get_full_name()
    get_tailor_name.short_description = 'Tailor'
    get_tailor_name.admin_order_field = 'tailor__shop_name'
    
    def get_service_area(self, obj):
        return f"{obj.service_area.name}, {obj.service_area.city}"
    get_service_area.short_description = 'Service Area'
    get_service_area.admin_order_field = 'service_area__name'
    
    # Grouped form
    fieldsets = (
        ('Service Area Assignment', {
            'fields': ('tailor', 'service_area', 'is_primary'),
            'description': 'Assign service area to tailor'
        }),
        ('Delivery Information', {
            'fields': ('delivery_fee', 'estimated_delivery_days'),
            'description': 'Optional delivery details for this area'
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
            'description': 'System timestamps'
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queries by selecting related objects."""
        return super().get_queryset(request).select_related(
            'tailor__user', 'service_area'
        )
