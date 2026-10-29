from django.core.management.base import BaseCommand

from apps.invoicing.models import TaxInvoice
from apps.invoicing.services.walk_in_invoice import issue_walk_in_tax_invoice


class Command(BaseCommand):
    help = 'Retry failed walk-in tax invoice submissions (ZATCA Tools).'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=50)

    def handle(self, *args, **options):
        limit = options['limit']
        qs = TaxInvoice.objects.filter(status=TaxInvoice.STATUS_FAILED).order_by('updated_at')[:limit]
        retried = 0
        for tax_invoice in qs:
            issue_walk_in_tax_invoice(tax_invoice.order_id)
            retried += 1
        self.stdout.write(self.style.SUCCESS(f'Retried {retried} failed tax invoice(s).'))
