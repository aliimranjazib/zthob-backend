from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.core.phone_format import normalize_phone_to_local, phone_lookup_variations
from apps.orders.models import Order

User = get_user_model()


class Command(BaseCommand):
    help = (
        'Diagnose duplicate/mismatched customer accounts for a phone number. '
        'Useful when POS walk-in customers cannot see orders in the customer app.'
    )

    def add_arguments(self, parser):
        parser.add_argument('phone', help='Phone number in any common format')

    def handle(self, *args, **options):
        phone_input = options['phone']
        local_phone = normalize_phone_to_local(phone_input)
        variations = phone_lookup_variations(phone_input)

        self.stdout.write(f'Input phone: {phone_input}')
        self.stdout.write(f'Local phone: {local_phone}')
        self.stdout.write(f'Lookup variations: {", ".join(variations)}')
        self.stdout.write('')

        users = User.objects.filter(phone__in=variations).order_by('id')
        if not users.exists():
            self.stdout.write(self.style.WARNING('No users found for this phone.'))
            return

        if users.count() > 1:
            self.stdout.write(
                self.style.ERROR(
                    f'Found {users.count()} user accounts for the same phone — '
                    'this usually explains missing orders in the customer app.'
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS(f'Found {users.count()} user account.'))

        for user in users:
            order_count = Order.objects.filter(customer=user).count()
            walk_in_count = Order.objects.filter(customer=user, service_mode='walk_in').count()
            pos_created = getattr(getattr(user, 'customer_profile', None), 'pos_created_by_id', None)

            self.stdout.write('')
            self.stdout.write(f'User ID: {user.id}')
            self.stdout.write(f'Username: {user.username}')
            self.stdout.write(f'Stored phone: {user.phone}')
            self.stdout.write(f'Role: {user.role}')
            self.stdout.write(f'Phone verified: {user.phone_verified}')
            self.stdout.write(f'Active: {user.is_active} | Deleted: {user.is_deleted}')
            self.stdout.write(f'POS created by user id: {pos_created or "-"}')
            self.stdout.write(f'Orders as customer: {order_count} (walk-in: {walk_in_count})')

            recent_orders = Order.objects.filter(customer=user).order_by('-created_at')[:5]
            for order in recent_orders:
                self.stdout.write(
                    f'  - Order #{order.order_number} id={order.id} '
                    f'status={order.status} service_mode={order.service_mode} '
                    f'tailor_id={order.tailor_id}'
                )

        self.stdout.write('')
        self.stdout.write(
            'If orders are on a different user than the one the client logs into, '
            'reassign order.customer in admin or merge the duplicate accounts.'
        )
