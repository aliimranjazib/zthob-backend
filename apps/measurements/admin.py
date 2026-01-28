"""
Django Admin Interface for Measurement Templates

Provides comprehensive admin interface with inline field editing,
validation, and user-friendly configuration options.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.db import models
from django.forms import TextInput, NumberInput
from .models import MeasurementTemplate, MeasurementField


class MeasurementFieldInline(admin.TabularInline):
    """Inline admin for measurement fields within template form"""
    model = MeasurementField
    extra = 1  # Show 1 empty form by default
    fields = [
        'order',
        'field_key',
        'display_name_en',
        'display_name_ar',
        'unit',
        'min_value',
        'max_value',
        'is_required',
        'category',
        'is_active',
    ]
    ordering = ['order', 'field_key']
    
    # Make the form more compact
    formfield_overrides = {
        models.CharField: {'widget': TextInput(attrs={'size': '20'})},
        models.DecimalField: {'widget': NumberInput(attrs={'size': '8'})},
    }
    
    class Media:
        css = {
            'all': ('admin/css/measurement_inline.css',)
        }


@admin.register(MeasurementTemplate)
class MeasurementTemplateAdmin(admin.ModelAdmin):
    """Admin interface for measurement templates"""
    
    list_display = [
        'name_en',
        'name_ar',
        'garment_type',
        'field_count_display',
        'is_default_display',
        'is_active_display',
        'updated_at',
    ]
    
    list_filter = [
        'garment_type',
        'is_default',
        'is_active',
        'created_at',
    ]
    
    search_fields = [
        'name_en',
        'name_ar',
        'description_en',
        'description_ar',
    ]
    
    readonly_fields = [
        'created_at',
        'updated_at',
        'field_count',
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                ('name_en', 'name_ar'),
                ('description_en', 'description_ar'),
            )
        }),
        ('Configuration', {
            'fields': (
                'garment_type',
                ('is_default', 'is_active'),
            )
        }),
        ('Metadata', {
            'fields': (
                'field_count',
                ('created_at', 'updated_at'),
            ),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [MeasurementFieldInline]
    
    actions = [
        'activate_templates',
        'deactivate_templates',
        'duplicate_template',
    ]
    
    def field_count_display(self, obj):
        """Display count of active fields"""
        count = obj.field_count
        color = 'green' if count > 0 else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            f"{count} field{'s' if count != 1 else ''}"
        )
    field_count_display.short_description = 'Active Fields'
    field_count_display.admin_order_field = 'field_count'
    
    def is_default_display(self, obj):
        """Display default status with icon"""
        if obj.is_default:
            return format_html(
                '<span style="color: green;">✓ Default</span>'
            )
        return format_html(
            '<span style="color: gray;">—</span>'
        )
    is_default_display.short_description = 'Default'
    is_default_display.admin_order_field = 'is_default'
    
    def is_active_display(self, obj):
        """Display active status with colored indicator"""
        if obj.is_active:
            return format_html(
                '<span style="color: green;">● Active</span>'
            )
        return format_html(
            '<span style="color: red;">● Inactive</span>'
        )
    is_active_display.short_description = 'Status'
    is_active_display.admin_order_field = 'is_active'
    
    def activate_templates(self, request, queryset):
        """Bulk action to activate selected templates"""
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            f'{updated} template(s) successfully activated.'
        )
    activate_templates.short_description = 'Activate selected templates'
    
    def deactivate_templates(self, request, queryset):
        """Bulk action to deactivate selected templates"""
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            f'{updated} template(s) successfully deactivated.'
        )
    deactivate_templates.short_description = 'Deactivate selected templates'
    
    def duplicate_template(self, request, queryset):
        """Duplicate selected template with all fields"""
        if queryset.count() != 1:
            self.message_user(
                request,
                'Please select exactly one template to duplicate.',
                level='error'
            )
            return
        
        original = queryset.first()
        
        # Create duplicate template
        duplicate = MeasurementTemplate.objects.create(
            name_en=f"{original.name_en} (Copy)",
            name_ar=f"{original.name_ar} (نسخة)",
            description_en=original.description_en,
            description_ar=original.description_ar,
            garment_type=original.garment_type,
            is_default=False,  # Copies are never default
            is_active=False,   # Copies start inactive
        )
        
        # Duplicate all fields
        fields_to_copy = original.fields.all()
        for field in fields_to_copy:
            MeasurementField.objects.create(
                template=duplicate,
                field_key=field.field_key,
                display_name_en=field.display_name_en,
                display_name_ar=field.display_name_ar,
                unit=field.unit,
                min_value=field.min_value,
                max_value=field.max_value,
                is_required=field.is_required,
                order=field.order,
                category=field.category,
                help_text_en=field.help_text_en,
                help_text_ar=field.help_text_ar,
                is_active=field.is_active,
            )
        
        self.message_user(
            request,
            f'Successfully created duplicate template: "{duplicate.name_en}" '
            f'with {fields_to_copy.count()} fields.'
        )
    duplicate_template.short_description = 'Duplicate selected template'
    
    def save_model(self, request, obj, form, change):
        """Override save to show helpful message"""
        super().save_model(request, obj, form, change)
        
        if not change:  # New template
            self.message_user(
                request,
                f'Template "{obj.name_en}" created successfully. '
                f'Don\'t forget to add measurement fields below!',
                level='success'
            )


@admin.register(MeasurementField)
class MeasurementFieldAdmin(admin.ModelAdmin):
    """Admin interface for individual measurement fields (optional standalone view)"""
    
    list_display = [
        'display_name_en',
        'display_name_ar',
        'field_key',
        'template',
        'unit',
        'value_range',
        'is_required',
        'order',
        'is_active',
    ]
    
    list_filter = [
        'template',
        'unit',
        'category',
        'is_required',
        'is_active',
    ]
    
    search_fields = [
        'field_key',
        'display_name_en',
        'display_name_ar',
        'template__name_en',
        'template__name_ar',
    ]
    
    list_editable = [
        'order',
        'is_active',
    ]
    
    readonly_fields = [
        'created_at',
        'updated_at',
    ]
    
    fieldsets = (
        ('Field Identification', {
            'fields': (
                'template',
                'field_key',
                ('display_name_en', 'display_name_ar'),
            )
        }),
        ('Measurement Configuration', {
            'fields': (
                'unit',
                ('min_value', 'max_value'),
                'is_required',
            )
        }),
        ('Display & Categorization', {
            'fields': (
                'order',
                'category',
                ('help_text_en', 'help_text_ar'),
            )
        }),
        ('Status', {
            'fields': (
                'is_active',
                ('created_at', 'updated_at'),
            )
        }),
    )
    
    def value_range(self, obj):
        """Display min-max value range"""
        return f"{obj.min_value} - {obj.max_value} {obj.unit}"
    value_range.short_description = 'Valid Range'
    
    actions = [
        'activate_fields',
        'deactivate_fields',
    ]
    
    def activate_fields(self, request, queryset):
        """Bulk action to activate selected fields"""
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            f'{updated} field(s) successfully activated.'
        )
    activate_fields.short_description = 'Activate selected fields'
    
    def deactivate_fields(self, request, queryset):
        """Bulk action to deactivate selected fields"""
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            f'{updated} field(s) successfully deactivated.'
        )
    deactivate_fields.short_description = 'Deactivate selected fields'
