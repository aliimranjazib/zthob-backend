from django.contrib import admin
from django.utils.html import format_html

from apps.documents.models import PdfDocumentSection, PdfDocumentTemplate


class PdfDocumentSectionInline(admin.TabularInline):
    model = PdfDocumentSection
    extra = 0
    ordering = ['display_order', 'id']
    fields = ['key', 'display_order', 'is_visible', 'settings']


@admin.register(PdfDocumentTemplate)
class PdfDocumentTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'version', 'engine', 'is_default', 'is_active', 'section_count']
    list_filter = ['engine', 'is_active', 'is_default']
    list_editable = ['is_default', 'is_active']
    search_fields = ['name', 'slug']
    inlines = [PdfDocumentSectionInline]
    fieldsets = (
        ('Template', {
            'fields': ('name', 'slug', 'version', 'engine', 'is_default', 'is_active'),
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',),
        }),
        ('How to change layout', {
            'description': format_html(
                'Reorder sections with <b>Display order</b> (lower prints first). '
                'Uncheck <b>Visible</b> to hide a block. '
                'Person-item settings JSON examples: '
                '<code>{}</code>',
                '{"measurement_cols": 5, "measurement_rows": 4, "show_sequence_numbers": true}',
            ),
            'fields': (),
        }),
    )

    def section_count(self, obj):
        visible = obj.sections.filter(is_visible=True).count()
        total = obj.sections.count()
        return f'{visible} visible / {total} total'
    section_count.short_description = 'Sections'
