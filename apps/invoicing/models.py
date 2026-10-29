from decimal import Decimal

from django.db import models

from apps.core.models import BaseModel


class TaxInvoice(BaseModel):
    """ZATCA simplified tax invoice issued for a walk-in order."""

    STATUS_PENDING = 'pending'
    STATUS_SUBMITTING = 'submitting'
    STATUS_ACCEPTED = 'accepted'
    STATUS_WARNINGS = 'warnings'
    STATUS_REJECTED = 'rejected'
    STATUS_FAILED = 'failed'

    STATUS_CHOICES = (
        (STATUS_PENDING, 'Pending'),
        (STATUS_SUBMITTING, 'Submitting'),
        (STATUS_ACCEPTED, 'Accepted'),
        (STATUS_WARNINGS, 'Accepted with warnings'),
        (STATUS_REJECTED, 'Rejected by ZATCA'),
        (STATUS_FAILED, 'Failed to submit'),
    )

    order = models.OneToOneField(
        'orders.Order',
        on_delete=models.CASCADE,
        related_name='tax_invoice',
    )
    shop = models.ForeignKey(
        'tailors.TailorProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tax_invoices',
    )
    external_id = models.CharField(max_length=64, unique=True, db_index=True)
    provider = models.CharField(max_length=32, default='zatca_tools')
    invoice_type = models.CharField(max_length=32, default='simplified')
    provider_number = models.CharField(max_length=64, blank=True, default='')
    uuid = models.UUIDField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )
    zatca_channel = models.CharField(max_length=32, blank=True, default='')
    zatca_icv = models.PositiveIntegerField(null=True, blank=True)
    taxable_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    vat_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    view_url = models.URLField(max_length=500, blank=True, default='')
    pdf_file = models.FileField(upload_to='tax_invoices/pdf/', blank=True, null=True)
    xml_file = models.FileField(upload_to='tax_invoices/xml/', blank=True, null=True)
    raw_response = models.JSONField(default=dict, blank=True)
    error_code = models.CharField(max_length=64, blank=True, default='')
    error_message = models.TextField(blank=True, default='')
    issued_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'TaxInvoice {self.provider_number or self.external_id} ({self.status})'

    @property
    def is_success(self):
        return self.status in (self.STATUS_ACCEPTED, self.STATUS_WARNINGS)
