"""
Management command to auto-collect walk-in orders that have been ready for pickup for more than 7 days.

Usage:
    python manage.py auto_collect_orders

This command should be run daily via cron job or task scheduler.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.orders.models import Order


class Command(BaseCommand):
    help = 'Auto-collect walk-in orders that have been ready for pickup for more than 7 days'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days after which to auto-collect (default: 7)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be collected without actually updating'
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        
        # Calculate the cutoff date
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Find walk-in orders that are ready for pickup and older than cutoff
        orders_to_collect = Order.objects.filter(
            service_mode='walk_in',
            status='ready_for_pickup',
            updated_at__lt=cutoff_date
        )
        
        count = orders_to_collect.count()
        
        if count == 0:
            self.stdout.write(
                self.style.SUCCESS(f'No orders found that need auto-collection')
            )
            return
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'DRY RUN: Would auto-collect {count} orders:')
            )
            for order in orders_to_collect:
                days_waiting = (timezone.now() - order.updated_at).days
                self.stdout.write(
                    f'  - Order #{order.order_number} (waiting {days_waiting} days)'
                )
        else:
            # Actually update the orders
            updated_count = 0
            for order in orders_to_collect:
                days_waiting = (timezone.now() - order.updated_at).days
                order.status = 'collected'
                order.save()
                updated_count += 1
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Auto-collected order #{order.order_number} (was waiting {days_waiting} days)'
                    )
                )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nSuccessfully auto-collected {updated_count} orders'
                )
            )
