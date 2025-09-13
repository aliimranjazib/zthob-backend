from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

# Register your models here.
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    # Simple, essential fields only
    list_display = ['username', 'email', 'role', 'is_active', 'date_joined']
    list_filter = ['role', 'is_active', 'date_joined']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    
    # Simplified fieldsets - group related fields
    fieldsets = (
        ('Basic Info', {'fields': ('username', 'email', 'first_name', 'last_name')}),
        ('Account Type', {'fields': ('role', 'is_active', 'is_staff')}),
        ('Contact', {'fields': ('phone',)}),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    # Simple add form
    add_fieldsets = (
        ('Create New User', {
            'classes': ('wide',),
            'fields': ('username', 'email', 'first_name', 'last_name', 'role', 'password1', 'password2'),
        }),
    )