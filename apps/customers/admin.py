from django.contrib import admin
from .models import CustomerProfile, Address, FamilyMember

# Register your models here.
@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    # Simple, essential fields
    list_display = ['user', 'gender', 'loyalty_points']
    list_filter = ['gender']
    search_fields = ['user__username', 'user__email']
    raw_id_fields = ['user', 'default_address']
    
    # Grouped fields for easier editing
    fieldsets = (
        ('Customer Info', {'fields': ('user', 'gender', 'date_of_birth')}),
        ('Loyalty & Tags', {'fields': ('loyalty_points', 'tags')}),
        ('Address', {'fields': ('default_address',)}),
    )

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    # Essential address info
    list_display = ['user', 'street', 'city', 'country', 'is_default']
    list_filter = ['country', 'is_default']
    search_fields = ['user__username', 'street', 'city']
    raw_id_fields = ['user']
    
    # Simple address form
    fieldsets = (
        ('Location', {'fields': ('street', 'city', 'state_province', 'country', 'zip_code')}),
        ('Settings', {'fields': ('user', 'is_default')}),
    )

@admin.register(FamilyMember)
class FamilyMemberAdmin(admin.ModelAdmin):
    # Essential family info
    list_display = ['user', 'name', 'relationship']
    list_filter = ['relationship']
    search_fields = ['user__username', 'name']
    raw_id_fields = ['user', 'address']
    
    # Simple family form
    fieldsets = (
        ('Family Info', {'fields': ('user', 'name', 'gender', 'relationship')}),
        ('Address', {'fields': ('address',)}),
        ('Measurements', {'fields': ('measurements',)}),
    )
