from rest_framework import serializers

from apps.invoicing.models import TaxInvoice


class TaxInvoiceSummarySerializer(serializers.ModelSerializer):
    mgask_order_number = serializers.CharField(source='order.order_number', read_only=True)
    pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = TaxInvoice
        fields = [
            'status',
            'invoice_type',
            'provider_number',
            'mgask_order_number',
            'taxable_amount',
            'vat_amount',
            'grand_total',
            'view_url',
            'pdf_url',
            'zatca_channel',
            'zatca_icv',
            'error_code',
            'error_message',
            'issued_at',
        ]

    def get_pdf_url(self, obj):
        request = self.context.get('request')
        if not request or not obj.pdf_file:
            return None
        return request.build_absolute_uri(
            f'/api/tailors/orders/{obj.order_id}/tax-invoice/download/'
        )
