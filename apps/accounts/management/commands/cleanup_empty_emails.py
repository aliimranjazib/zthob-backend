"""
Django management command to clean up empty email strings in user accounts.

This command fixes the UNIQUE constraint issue where multiple users have empty
email strings ('') instead of NULL values, which violates the unique constraint.

Usage:
    python manage.py cleanup_empty_emails
    python manage.py cleanup_empty_emails --dry-run  # Preview changes without applying
    python manage.py cleanup_empty_emails --verbose   # Show detailed output
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from apps.accounts.models import CustomUser


class Command(BaseCommand):
    help = 'Clean up empty email strings by setting them to NULL to fix UNIQUE constraint issues'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without actually updating the database',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed information about each user being updated',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Skip confirmation prompt',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        verbose = options['verbose']
        force = options['force']

        # Find users with empty email strings
        users_with_empty_email = CustomUser.objects.filter(email='')
        count = users_with_empty_email.count()

        if count == 0:
            self.stdout.write(
                self.style.SUCCESS('✓ No users with empty email strings found. Database is clean!')
            )
            return

        # Show summary
        self.stdout.write(
            self.style.WARNING(
                f'\n⚠ Found {count} user(s) with empty email strings that need to be fixed.\n'
            )
        )

        if verbose:
            self.stdout.write('Users that will be updated:')
            self.stdout.write('-' * 80)
            for user in users_with_empty_email[:20]:  # Show first 20
                self.stdout.write(
                    f'  ID: {user.id:6d} | Username: {user.username:20s} | '
                    f'Phone: {user.phone or "N/A":15s} | Email: "{user.email}"'
                )
            if count > 20:
                self.stdout.write(f'  ... and {count - 20} more users')
            self.stdout.write('-' * 80)

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    '\n🔍 DRY RUN MODE - No changes will be made to the database.\n'
                )
            )
            self.stdout.write(
                f'Would update {count} user(s) to set email=None instead of empty string.'
            )
            return

        # Confirm before proceeding (unless --force is used)
        if not force:
            self.stdout.write(
                self.style.WARNING(
                    '\nThis will update all users with empty email strings to have email=None.\n'
                )
            )
            confirm = input('Do you want to proceed? (yes/no): ')
            if confirm.lower() not in ['yes', 'y']:
                self.stdout.write(self.style.ERROR('Operation cancelled.'))
                return

        # Perform the update
        try:
            with transaction.atomic():
                updated_count = users_with_empty_email.update(email=None)
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'\n✓ Successfully updated {updated_count} user(s).\n'
                    )
                )
                
                # Verify the fix
                remaining_empty = CustomUser.objects.filter(email='').count()
                if remaining_empty == 0:
                    self.stdout.write(
                        self.style.SUCCESS(
                            '✓ Verification: No users with empty email strings remain.'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'⚠ Warning: {remaining_empty} user(s) still have empty email strings.'
                        )
                    )

                # Show statistics
                total_users = CustomUser.objects.count()
                users_with_null_email = CustomUser.objects.filter(email__isnull=True).count()
                users_with_email = CustomUser.objects.exclude(email__isnull=True).exclude(email='').count()
                
                self.stdout.write('\n📊 Email Statistics:')
                self.stdout.write(f'  Total users: {total_users}')
                self.stdout.write(f'  Users with NULL email: {users_with_null_email}')
                self.stdout.write(f'  Users with valid email: {users_with_email}')
                self.stdout.write(f'  Users with empty string email: {remaining_empty}')

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f'\n✗ Error occurred during cleanup: {str(e)}'
                )
            )
            raise

