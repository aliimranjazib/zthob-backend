from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from apps.orders.models import Order
from .services import WalletService
from .models import PayoutRequest, RiderPayoutRequest
from apps.notifications.services import NotificationService

@receiver(post_save, sender=Order)
def handle_order_financials(sender, instance, created, **kwargs):
    """
    Signal receiver to process tailor earnings when an order is completed.
    Completed statuses: 'delivered' (Home Delivery) or 'collected' (Walk-In).
    """
    # We only process if the order is paid and reached a final completed status
    if instance.status in ['delivered', 'collected'] and instance.payment_status == 'paid':
        WalletService.process_order_earning(instance)
        WalletService.process_rider_order_earning(instance)

@receiver(pre_save, sender=PayoutRequest)
@receiver(pre_save, sender=RiderPayoutRequest)
def track_payout_status(sender, instance, **kwargs):
    """
    Store the old status to check if it changed in post_save.
    """
    if instance.pk:
        try:
            instance._old_status = sender.objects.get(pk=instance.pk).status
        except sender.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None

@receiver(post_save, sender=PayoutRequest)
@receiver(post_save, sender=RiderPayoutRequest)
def handle_payout_notifications(sender, instance, created, **kwargs):
    """
    Send notification to tailor when payout status changes.
    """
    old_status = getattr(instance, '_old_status', None)
    
    if not created and old_status != instance.status:
        # Status has changed
        if instance.status in ['approved', 'rejected', 'paid']:
            NotificationService.send_payout_notification(instance)
