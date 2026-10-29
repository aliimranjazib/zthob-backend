from django.core.management.base import BaseCommand

from apps.invoicing.providers.zatca_tools import ZatcaToolsClient, ZatcaToolsError


class Command(BaseCommand):
    help = 'Verify ZATCA Tools API key and print connection/quota (GET /v1/account).'

    def handle(self, *args, **options):
        client = ZatcaToolsClient()
        if not client.configured:
            self.stderr.write(self.style.ERROR('ZATCA_TOOLS_API_KEY is not set.'))
            return
        try:
            data = client.get_account()
        except ZatcaToolsError as exc:
            self.stderr.write(self.style.ERROR(f'{exc.code}: {exc.message}'))
            return
        zatca = data.get('zatca') or {}
        quota = data.get('quota') or {}
        self.stdout.write(self.style.SUCCESS('ZATCA Tools account OK'))
        self.stdout.write(f"  name: {data.get('name')}")
        self.stdout.write(f"  vat_number: {data.get('vat_number')}")
        self.stdout.write(f"  zatca.connected: {zatca.get('connected')}")
        self.stdout.write(f"  zatca.environment: {zatca.get('environment')}")
        self.stdout.write(f"  quota: {quota}")
