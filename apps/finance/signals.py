from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.orders.models import Order
from .services import WalletService

@receiver(post_save, sender=Order)
def handle_order_financials(sender, instance, created, **kwargs):
    """
    Signal receiver to process tailor earnings when an order is completed.
    Completed statuses: 'delivered' (Home Delivery) or 'collected' (Walk-In).
    """
    # We only process if the order is paid and reached a final completed status
    if instance.status in ['delivered', 'collected'] and instance.payment_status == 'paid':
        WalletService.process_order_earning(instance)
