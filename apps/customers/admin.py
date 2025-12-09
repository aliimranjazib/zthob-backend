from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.contrib import messages
from .models import CustomerProfile, Address, FamilyMember, FabricFavorite


# ============================================================================
# INLINE ADMIN CLASSES
# ============================================================================

class AddressInline(admin.TabularInline):
    """Inline admin for Addresses - shows addresses directly in Customer detail view"""
    model = Address
    extra = 0
    fields = [
        'street',
        'city',
        'state_province',
        'country',
        'zip_code',
        'is_default',
        'address_tag',
    ]
    readonly_fields = []
    can_delete = True
    show_change_link = True


class FamilyMemberInline(admin.TabularInline):
    """Inline admin for FamilyMembers - shows family members directly in Customer detail view"""
    model = FamilyMember
    extra = 0
    fields = [
        'name',
        'gender',
        'relationship',
        'address',
    ]
    readonly_fields = []
    can_delete = True
    show_change_link = True
    raw_id_fields = ['address']


# ============================================================================
# CUSTOM FILTERS
# ============================================================================

class AddressCountryFilter(admin.SimpleListFilter):
    """Custom filter for address countries"""
    title = 'Country'
    parameter_name = 'country_filter'
    
    def lookups(self, request, model_admin):
        countries = Address.objects.values_list('country', flat=True).distinct()
        return [(country, country) for country in sorted(countries) if country]
    
    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(country=self.value())


class DefaultAddressFilter(admin.SimpleListFilter):
    """Filter for default addresses"""
    title = 'Default Address'
    parameter_name = 'is_default'
    
    def lookups(self, request, model_admin):
        return (
            ('yes', 'Yes'),
            ('no', 'No'),
        )
    
    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(is_default=True)
        elif self.value() == 'no':
            return queryset.filter(is_default=False)


# ============================================================================
# ADDRESS ADMIN
# ============================================================================

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    """
    Professional Address Admin Interface
    """
    
    list_display = [
        'user_link',
        'address_display',
        'city',
        'country',
        'address_tag_badge',
        'is_default_badge',
        'has_coordinates',
    ]
    
    list_display_links = ['address_display']
    
    list_filter = [
        AddressCountryFilter,
        DefaultAddressFilter,
        'address_tag',
        'is_default',
        'country',
    ]
    
    search_fields = [
        'user__username',
        'user__email',
        'street',
        'city',
        'state_province',
        'zip_code',
        'formatted_address',
    ]
    
    raw_id_fields = ['user']
    
    readonly_fields = []
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Address Details', {
            'fields': (
                'street',
                'city',
                'state_province',
                'zip_code',
                'country',
            )
        }),
        ('Location Data', {
            'fields': (
                'latitude',
                'longitude',
                'formatted_address',
            ),
            'classes': ('collapse',)
        }),
        ('Address Settings', {
            'fields': (
                'address_tag',
                'is_default',
                'extra_info',
            )
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
    
    def address_display(self, obj):
        """Display formatted address"""
        parts = []
        if obj.street:
            parts.append(obj.street)
        if obj.city:
            parts.append(obj.city)
        if obj.state_province:
            parts.append(obj.state_province)
        if obj.zip_code:
            parts.append(obj.zip_code)
        if parts:
            address = ', '.join(parts)
            return format_html('<strong>{}</strong>', address)
        return format_html('<em style="color: #999;">No address</em>')
    address_display.short_description = 'Address'
    
    def address_tag_badge(self, obj):
        """Display address tag with badge"""
        colors = {
            'home': '#28a745',
            'office': '#17a2b8',
            'work': '#ffc107',
            'other': '#6c757d',
        }
        color = colors.get(obj.address_tag, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.get_address_tag_display()
        )
    address_tag_badge.short_description = 'Tag'
    address_tag_badge.admin_order_field = 'address_tag'
    
    def is_default_badge(self, obj):
        """Display default status"""
        if obj.is_default:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">Default</span>'
            )
        return '-'
    is_default_badge.short_description = 'Default'
    is_default_badge.admin_order_field = 'is_default'
    
    def has_coordinates(self, obj):
        """Check if address has GPS coordinates"""
        if obj.latitude and obj.longitude:
            return format_html(
                '<span style="color: #28a745;">✓</span>'
            )
        return format_html('<span style="color: #dc3545;">✗</span>')
    has_coordinates.short_description = 'GPS'
    
    actions = ['set_as_default', 'export_addresses_csv']
    
    def set_as_default(self, request, queryset):
        """Set selected addresses as default for their users"""
        count = 0
        for address in queryset:
            if address.user:
                # Unset other defaults for this user
                Address.objects.filter(user=address.user, is_default=True).update(is_default=False)
                address.is_default = True
                address.save()
                count += 1
        self.message_user(
            request,
            f'Successfully set {count} address(es) as default.',
            messages.SUCCESS
        )
    set_as_default.short_description = 'Set selected addresses as default'
    
    def export_addresses_csv(self, request, queryset):
        """Export addresses to CSV"""
        import csv
        from django.http import HttpResponse
        from datetime import datetime
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="addresses_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'User',
            'Street',
            'City',
            'State/Province',
            'Zip Code',
            'Country',
            'Tag',
            'Is Default',
            'Latitude',
            'Longitude',
        ])
        
        for address in queryset:
            writer.writerow([
                address.user.username if address.user else '',
                address.street,
                address.city,
                address.state_province or '',
                address.zip_code or '',
                address.country,
                address.get_address_tag_display(),
                'Yes' if address.is_default else 'No',
                str(address.latitude) if address.latitude else '',
                str(address.longitude) if address.longitude else '',
            ])
        
        return response
    export_addresses_csv.short_description = 'Export selected addresses to CSV'
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related('user')


# ============================================================================
# CUSTOMER PROFILE ADMIN
# ============================================================================

@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    """
    Professional Customer Profile Admin Interface
    """
    
    list_display = [
        'user_link',
        'full_name_display',
        'gender',
        'date_of_birth_display',
        'loyalty_points_badge',
        'default_address_link',
        'addresses_count',
        'family_members_count',
    ]
    
    list_display_links = ['user_link']
    
    list_filter = [
        'gender',
        'date_of_birth',
    ]
    
    search_fields = [
        'user__username',
        'user__email',
        'user__first_name',
        'user__last_name',
        'tags',
    ]
    
    raw_id_fields = ['user', 'default_address']
    
    readonly_fields = []
    
    # Note: AddressInline and FamilyMemberInline cannot be used here because
    # Address and FamilyMember have ForeignKeys to User, not CustomerProfile.
    # They are accessible through the user relationship.
    # Use the addresses_count and family_members_count display methods to navigate to them.
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Personal Information', {
            'fields': (
                'gender',
                'date_of_birth',
            )
        }),
        ('Loyalty & Preferences', {
            'fields': (
                'loyalty_points',
                'tags',
            )
        }),
        ('Default Address', {
            'fields': ('default_address',)
        }),
    )
    
    list_per_page = 50
    
    def user_link(self, obj):
        """Clickable user link"""
        if obj.user and obj.user.pk:
            try:
                url = reverse('admin:accounts_customuser_change', args=[obj.user.pk])
                return format_html('<a href="{}"><strong>{}</strong></a>', url, obj.user.username or 'No username')
            except Exception:
                return obj.user.username or '-'
        return '-'
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__username'
    
    def full_name_display(self, obj):
        """Display full name"""
        if obj.user:
            full_name = obj.user.get_full_name()
            if full_name:
                return format_html('<strong>{}</strong>', full_name)
            return obj.user.username
        return '-'
    full_name_display.short_description = 'Full Name'
    
    def date_of_birth_display(self, obj):
        """Format date of birth"""
        if obj.date_of_birth:
            return obj.date_of_birth.strftime('%Y-%m-%d')
        return format_html('<em style="color: #999;">Not set</em>')
    date_of_birth_display.short_description = 'Date of Birth'
    date_of_birth_display.admin_order_field = 'date_of_birth'
    
    def loyalty_points_badge(self, obj):
        """Display loyalty points with badge"""
        points = obj.loyalty_points or 0
        color = '#28a745' if points > 0 else '#6c757d'
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 10px; border-radius: 4px; font-weight: bold;">{} pts</span>',
            color,
            points
        )
    loyalty_points_badge.short_description = 'Loyalty Points'
    loyalty_points_badge.admin_order_field = 'loyalty_points'
    
    def default_address_link(self, obj):
        """Link to default address"""
        if obj.default_address:
            try:
                url = reverse('admin:customers_address_change', args=[obj.default_address.pk])
                street = obj.default_address.street or 'No street'
                city = obj.default_address.city or 'No city'
                return format_html(
                    '<a href="{}">{}, {}</a>',
                    url,
                    street,
                    city
                )
            except Exception:
                return format_html('<em style="color: #999;">Invalid address</em>')
        return format_html('<em style="color: #999;">No default address</em>')
    default_address_link.short_description = 'Default Address'
    
    def addresses_count(self, obj):
        """Count of addresses"""
        if obj.user:
            count = obj.user.addresses.count()
            if count > 0:
                url = reverse('admin:customers_address_changelist')
                url += f'?user__id__exact={obj.user.pk}'
                return format_html('<a href="{}">{} address{}</a>', url, count, 'es' if count != 1 else '')
        return '0'
    addresses_count.short_description = 'Addresses'
    
    def family_members_count(self, obj):
        """Count of family members"""
        if obj.user:
            count = obj.user.family_profile.count()
            if count > 0:
                url = reverse('admin:customers_familymember_changelist')
                url += f'?user__id__exact={obj.user.pk}'
                return format_html('<a href="{}">{} member{}</a>', url, count, 's' if count != 1 else '')
        return '0'
    family_members_count.short_description = 'Family Members'
    
    actions = ['add_loyalty_points', 'reset_loyalty_points', 'export_profiles_csv']
    
    def add_loyalty_points(self, request, queryset):
        """Add loyalty points to selected profiles"""
        count = 0
        for profile in queryset:
            profile.loyalty_points = (profile.loyalty_points or 0) + 100
            profile.save()
            count += 1
        self.message_user(
            request,
            f'Successfully added 100 loyalty points to {count} profile(s).',
            messages.SUCCESS
        )
    add_loyalty_points.short_description = 'Add 100 loyalty points to selected profiles'
    
    def reset_loyalty_points(self, request, queryset):
        """Reset loyalty points to 0"""
        count = queryset.update(loyalty_points=0)
        self.message_user(
            request,
            f'Successfully reset loyalty points for {count} profile(s).',
            messages.SUCCESS
        )
    reset_loyalty_points.short_description = 'Reset loyalty points to 0'
    
    def export_profiles_csv(self, request, queryset):
        """Export customer profiles to CSV"""
        import csv
        from django.http import HttpResponse
        from datetime import datetime
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="customer_profiles_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Username',
            'Email',
            'Full Name',
            'Gender',
            'Date of Birth',
            'Loyalty Points',
            'Tags',
        ])
        
        for profile in queryset:
            writer.writerow([
                profile.user.username if profile.user else '',
                profile.user.email if profile.user else '',
                profile.user.get_full_name() if profile.user else '',
                profile.gender or '',
                profile.date_of_birth.strftime('%Y-%m-%d') if profile.date_of_birth else '',
                profile.loyalty_points or 0,
                profile.tags or '',
            ])
        
        return response
    export_profiles_csv.short_description = 'Export selected profiles to CSV'
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related('user', 'default_address').prefetch_related(
            'user__addresses',
            'user__family_profile'
        )


# ============================================================================
# FAMILY MEMBER ADMIN
# ============================================================================

@admin.register(FamilyMember)
class FamilyMemberAdmin(admin.ModelAdmin):
    """
    Professional Family Member Admin Interface
    """
    
    list_display = [
        'user_link',
        'name',
        'gender',
        'relationship',
        'address_link',
        'has_measurements',
    ]
    
    list_display_links = ['name']
    
    list_filter = [
        'gender',
        'relationship',
    ]
    
    search_fields = [
        'user__username',
        'user__email',
        'name',
        'relationship',
    ]
    
    raw_id_fields = ['user', 'address']
    
    readonly_fields = []
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Family Member Information', {
            'fields': (
                'name',
                'gender',
                'relationship',
            )
        }),
        ('Address', {
            'fields': ('address',)
        }),
        ('Measurements', {
            'fields': ('measurements',),
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
    
    def address_link(self, obj):
        """Link to address"""
        if obj.address:
            try:
                url = reverse('admin:customers_address_change', args=[obj.address.pk])
                street = obj.address.street or 'No street'
                city = obj.address.city or 'No city'
                return format_html(
                    '<a href="{}">{}, {}</a>',
                    url,
                    street,
                    city
                )
            except Exception:
                return format_html('<em style="color: #999;">Invalid address</em>')
        return format_html('<em style="color: #999;">No address</em>')
    address_link.short_description = 'Address'
    
    def has_measurements(self, obj):
        """Check if family member has measurements"""
        if obj.measurements and isinstance(obj.measurements, dict) and obj.measurements:
            return format_html('<span style="color: #28a745;">✓</span>')
        return format_html('<span style="color: #dc3545;">✗</span>')
    has_measurements.short_description = 'Measurements'
    
    actions = ['export_family_members_csv']
    
    def export_family_members_csv(self, request, queryset):
        """Export family members to CSV"""
        import csv
        from django.http import HttpResponse
        from datetime import datetime
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="family_members_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'User',
            'Name',
            'Gender',
            'Relationship',
            'Address',
            'Has Measurements',
        ])
        
        for member in queryset:
            writer.writerow([
                member.user.username if member.user else '',
                member.name,
                member.gender or '',
                member.relationship or '',
                f"{member.address.street or ''}, {member.address.city or ''}".strip(', ') if member.address else '',
                'Yes' if (member.measurements and isinstance(member.measurements, dict) and member.measurements) else 'No',
            ])
        
        return response
    export_family_members_csv.short_description = 'Export selected family members to CSV'
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related('user', 'address')


# ============================================================================
# FABRIC FAVORITE ADMIN
# ============================================================================

@admin.register(FabricFavorite)
class FabricFavoriteAdmin(admin.ModelAdmin):
    """
    Professional Fabric Favorite Admin Interface
    """
    
    list_display = [
        'user_link',
        'fabric_link',
        'fabric_name',
        'fabric_tailor',
        'created_at_display',
    ]
    
    list_display_links = ['fabric_link']
    
    list_filter = [
        'created_at',
    ]
    
    search_fields = [
        'user__username',
        'user__email',
        'fabric__name',
        'fabric__sku',
        'fabric__tailor__shop_name',
    ]
    
    raw_id_fields = ['user', 'fabric']
    
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Fabric Information', {
            'fields': ('fabric',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
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
    
    def fabric_name(self, obj):
        """Display fabric name"""
        if obj.fabric:
            return format_html('<strong>{}</strong>', obj.fabric.name)
        return '-'
    fabric_name.short_description = 'Fabric Name'
    
    def fabric_tailor(self, obj):
        """Display fabric tailor"""
        if obj.fabric and obj.fabric.tailor:
            try:
                url = reverse('admin:tailors_tailorprofile_change', args=[obj.fabric.tailor.pk])
                shop_name = obj.fabric.tailor.shop_name or obj.fabric.tailor.user.get_full_name()
                return format_html('<a href="{}">{}</a>', url, shop_name)
            except Exception:
                return obj.fabric.tailor.shop_name or '-'
        return '-'
    fabric_tailor.short_description = 'Tailor'
    
    def created_at_display(self, obj):
        """Format created_at"""
        if obj.created_at:
            return obj.created_at.strftime('%Y-%m-%d %H:%M:%S')
        return '-'
    created_at_display.short_description = 'Favorited At'
    created_at_display.admin_order_field = 'created_at'
    
    actions = ['export_favorites_csv']
    
    def export_favorites_csv(self, request, queryset):
        """Export favorites to CSV"""
        import csv
        from django.http import HttpResponse
        from datetime import datetime
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="fabric_favorites_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'User',
            'User Email',
            'Fabric Name',
            'Fabric SKU',
            'Fabric Price',
            'Tailor',
            'Favorited At',
        ])
        
        for favorite in queryset:
            writer.writerow([
                favorite.user.username if favorite.user else '',
                favorite.user.email if favorite.user else '',
                favorite.fabric.name if favorite.fabric else '',
                favorite.fabric.sku if favorite.fabric else '',
                str(favorite.fabric.price) if favorite.fabric else '',
                favorite.fabric.tailor.shop_name if favorite.fabric and favorite.fabric.tailor else '',
                favorite.created_at.strftime('%Y-%m-%d %H:%M:%S') if favorite.created_at else '',
            ])
        
        return response
    export_favorites_csv.short_description = 'Export selected favorites to CSV'
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related('user', 'fabric', 'fabric__tailor', 'fabric__tailor__user')
