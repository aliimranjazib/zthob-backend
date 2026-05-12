from celery import shared_task
from django.contrib.auth import get_user_model
from .services import NotificationService
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

@shared_task(name="apps.notifications.tasks.send_notification_task")
def send_notification_task(user_id, title, body, notification_type, category, data=None, priority='high'):
    """
    Background task to send push notification via Firebase.
    """
    try:
        user = User.objects.get(id=user_id)
        success = NotificationService.send_notification(
            user=user,
            title=title,
            body=body,
            notification_type=notification_type,
            category=category,
            data=data,
            priority=priority
        )
        return success
    except User.DoesNotExist:
        logger.error(f"User with id {user_id} not found for notification")
        return False
@shared_task(name="apps.notifications.tasks.send_order_status_notification_task")
def send_order_status_notification_task(order_id, old_status, new_status, user_id=None):
    from apps.orders.models import Order
    from .services import NotificationService
    try:
        order = Order.objects.get(id=order_id)
        user = User.objects.get(id=user_id) if user_id else None
        NotificationService.send_order_status_notification(order, old_status, new_status, user)
        return True
    except Exception as e:
        logger.error(f"Error in send_order_status_notification_task: {str(e)}")
        return False

@shared_task(name="apps.notifications.tasks.send_tailor_status_notification_task")
def send_tailor_status_notification_task(order_id, old_status, new_status, user_id=None):
    from apps.orders.models import Order
    from .services import NotificationService
    try:
        order = Order.objects.get(id=order_id)
        user = User.objects.get(id=user_id) if user_id else None
        NotificationService.send_tailor_status_notification(order, old_status, new_status, user)
        return True
    except Exception as e:
        logger.error(f"Error in send_tailor_status_notification_task: {str(e)}")
        return False

@shared_task(name="apps.notifications.tasks.send_rider_status_notification_task")
def send_rider_status_notification_task(order_id, old_status, new_status, user_id=None):
    from apps.orders.models import Order
    from .services import NotificationService
    try:
        order = Order.objects.get(id=order_id)
        user = User.objects.get(id=user_id) if user_id else None
        NotificationService.send_rider_status_notification(order, old_status, new_status, user)
        return True
    except Exception as e:
        logger.error(f"Error in send_rider_status_notification_task: {str(e)}")
        return False
