"""
Signals for delivery tracking.
Automatically creates tracking when rider is assigned to an order.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.orders.models import Order
from apps.deliveries.models import DeliveryTracking
from apps.deliveries.services import DeliveryTrackingService


@receiver(post_save, sender=Order)
def create_delivery_tracking_on_rider_assignment(sender, instance, created, **kwargs):
    """
    Automatically create or sync delivery tracking when a rider is assigned to an order.
    """
    if instance.status == 'cancelled':
        return

    active_rider = DeliveryTrackingService.resolve_active_tracking_rider(instance)
    if not active_rider:
        return

    try:
        DeliveryTrackingService.sync_tracking_rider_for_order(instance)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(
            "Failed to create/sync delivery tracking for order %s: %s",
            instance.order_number,
            str(e),
        )


@receiver(post_save, sender=Order)
def update_tracking_status_on_order_status_change(sender, instance, **kwargs):
    """
    Update delivery tracking status when order status changes.
    """
    if instance.rider:
        try:
            tracking = DeliveryTracking.objects.get(order=instance, is_active=True)
            
            # Map order status to tracking status
            status_mapping = {
                'ready_for_delivery': 'on_way_to_pickup',
                'delivered': 'delivered',
                'cancelled': 'cancelled',
            }
            
            if instance.status in status_mapping:
                new_tracking_status = status_mapping[instance.status]
                if tracking.current_status != new_tracking_status:
                    DeliveryTrackingService.update_status(
                        tracking=tracking,
                        new_status=new_tracking_status,
                        notes=f"Status updated from order status change: {instance.status}"
                    )
        except DeliveryTracking.DoesNotExist:
            pass
        except Exception as e:
            # Log error but don't fail the order save
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to update delivery tracking for order {instance.order_number}: {str(e)}")

