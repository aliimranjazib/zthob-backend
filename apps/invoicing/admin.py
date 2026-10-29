from django.contrib import admin

from apps.invoicing.models import TaxInvoice


@admin.register(TaxInvoice)
class TaxInvoiceAdmin(admin.ModelAdmin):
    list_display = (
        'external_id',
        'provider_number',
        'status',
        'order',
        'grand_total',
        'issued_at',
        'created_at',
    )
    list_filter = ('status', 'invoice_type', 'provider')
    search_fields = ('external_id', 'provider_number', 'order__order_number')
    readonly_fields = ('raw_response', 'created_at', 'updated_at')
