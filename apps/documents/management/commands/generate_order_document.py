from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.documents.service import generate_order_document, generate_order_html
from apps.orders.models import Order


class Command(BaseCommand):
    help = 'Generate an order document as PDF or HTML using the template engine.'

    def add_arguments(self, parser):
        parser.add_argument('order_id', type=int)
        parser.add_argument('--lang', default='ar', choices=['en', 'ar', 'ur'])
        parser.add_argument('--engine', default='auto', choices=['auto', 'html', 'reportlab'])
        parser.add_argument('--format', dest='output_format', default='pdf', choices=['pdf', 'html'])
        parser.add_argument(
            '--output',
            default='',
            help='Output path. Defaults to Desktop/order_<number>.pdf|.html',
        )

    def handle(self, *args, **options):
        try:
            order = Order.objects.select_related(
                'customer',
                'tailor',
                'tailor__tailor_profile',
                'measurement_rider__rider_profile',
                'delivery_rider__rider_profile',
                'delivery_address',
            ).prefetch_related(
                'order_items__fabric',
                'order_items__family_member',
                'order_items__customer_fabric_images',
                'status_history__changed_by',
            ).get(id=options['order_id'])
        except Order.DoesNotExist as exc:
            raise CommandError(f'Order {options["order_id"]} not found') from exc

        suffix = 'html' if options['output_format'] == 'html' else 'pdf'
        output = Path(options['output']).expanduser() if options['output'] else (
            Path.home() / 'Desktop' / f'order_{order.order_number}.{suffix}'
        )
        output.parent.mkdir(parents=True, exist_ok=True)

        if options['output_format'] == 'html':
            html, _context, _layout = generate_order_html(order, lang=options['lang'])
            output.write_text(html, encoding='utf-8')
        else:
            pdf_bytes = generate_order_document(
                order,
                lang=options['lang'],
                engine=options['engine'],
            )
            output.write_bytes(pdf_bytes)

        self.stdout.write(self.style.SUCCESS(f'Wrote {output}'))
