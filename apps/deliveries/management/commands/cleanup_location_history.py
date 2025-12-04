"""
Management command to clean up location history older than 30 days.
Should be run daily via cron job.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.deliveries.models import LocationHistory


class Command(BaseCommand):
    help = 'Clean up location history older than 30 days'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days to keep location history (default: 30)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        
        # Calculate cutoff date
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Find old location history entries
        old_locations = LocationHistory.objects.filter(created_at__lt=cutoff_date)
        count = old_locations.count()
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'DRY RUN: Would delete {count} location history entries older than {days} days (before {cutoff_date})'
                )
            )
            
            # Show some examples
            if count > 0:
                self.stdout.write('\nSample entries that would be deleted:')
                for loc in old_locations[:5]:
                    self.stdout.write(
                        f'  - ID {loc.id}: Order {loc.delivery_tracking.order.order_number}, '
                        f'Location ({loc.latitude}, {loc.longitude}), Created: {loc.created_at}'
                    )
                if count > 5:
                    self.stdout.write(f'  ... and {count - 5} more entries')
        else:
            if count == 0:
                self.stdout.write(
                    self.style.SUCCESS(f'No location history entries older than {days} days found.')
                )
            else:
                # Delete old entries
                deleted_count, _ = old_locations.delete()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully deleted {deleted_count} location history entries older than {days} days.'
                    )
                )

