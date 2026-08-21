from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from apps.documents.models import PdfDocumentSection, PdfDocumentTemplate

PDF_LAYOUT_STUDIO_URL_NAME = 'documents:pdf-layout-studio'


def pdf_layout_studio_url():
    return reverse(PDF_LAYOUT_STUDIO_URL_NAME)


class PdfDocumentSectionInline(admin.TabularInline):
    model = PdfDocumentSection
    extra = 0
    ordering = ['display_order', 'id']
    fields = ['key', 'display_order', 'is_visible', 'settings']


@admin.register(PdfDocumentTemplate)
class PdfDocumentTemplateAdmin(admin.ModelAdmin):
    change_list_template = 'admin/documents/pdfdocumenttemplate/change_list.html'
    change_form_template = 'admin/documents/pdfdocumenttemplate/change_form.html'
    list_display = ['name', 'slug', 'version', 'engine', 'is_default', 'is_active', 'section_count']
    list_filter = ['engine', 'is_active', 'is_default']
    list_editable = ['is_default', 'is_active']
    search_fields = ['name', 'slug']
    inlines = [PdfDocumentSectionInline]

    def get_fieldsets(self, request, obj=None):
        return (
            ('Template', {
                'fields': ('name', 'slug', 'version', 'engine', 'is_default', 'is_active'),
            }),
            ('Notes', {
                'fields': ('notes',),
                'classes': ('collapse',),
            }),
            ('How to change layout', {
                'description': format_html(
                    'Use <a href="{}" target="_blank" rel="noopener"><b>PDF Layout Studio</b></a> '
                    'to drag sections, configure the measurement grid, and preview Arabic/English PDFs. '
                    'Advanced: reorder sections with <b>Display order</b> (lower prints first), '
                    'uncheck <b>Visible</b> to hide a block. '
                    'Person-item settings JSON examples: '
                    '<code>{}</code>',
                    pdf_layout_studio_url(),
                    '{"measurement_cols": 5, "measurement_rows": 4, "show_sequence_numbers": true}',
                ),
                'fields': (),
            }),
        )

    def changelist_view(self, request, extra_context=None):
        extra_context = {**(extra_context or {}), 'pdf_layout_studio_url': pdf_layout_studio_url()}
        return super().changelist_view(request, extra_context=extra_context)

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        extra_context = {**(extra_context or {}), 'pdf_layout_studio_url': pdf_layout_studio_url()}
        return super().changeform_view(request, object_id, form_url, extra_context=extra_context)

    def section_count(self, obj):
        visible = obj.sections.filter(is_visible=True).count()
        total = obj.sections.count()
        return f'{visible} visible / {total} total'
    section_count.short_description = 'Sections'
