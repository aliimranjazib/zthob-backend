from datetime import datetime

from django.core.management.base import BaseCommand

from apps.orders.daily_sales_whatsapp import report_date_for_job, run_daily_sales_whatsapp_job


class Command(BaseCommand):
    help = 'Send mgask_daily_sales_report to eligible tailor shops (manual / cron test).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Report calendar date YYYY-MM-DD (default: yesterday in WSLA_DAILY_SALES_REPORT_TZ)',
        )

    def handle(self, *args, **options):
        report_date = None
        raw = options.get('date')
        if raw:
            report_date = datetime.strptime(raw, '%Y-%m-%d').date()
        else:
            report_date = report_date_for_job()

        stats = run_daily_sales_whatsapp_job(report_date=report_date)
        self.stdout.write(
            self.style.SUCCESS(
                f'Daily sales WhatsApp for {report_date}: {stats}'
            )
        )
