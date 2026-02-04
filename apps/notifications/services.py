import logging
from typing import List, Dict, Optional
from django.conf import settings
from django.utils import timezone
from .models import FCMDeviceToken, NotificationLog
from zthob.translations import translate_message, get_language_from_request

# Import Firebase Admin SDK
try:
    from firebase_admin import messaging, credentials, initialize_app
    import firebase_admin
    FIREBASE_SDK_AVAILABLE = True
except ImportError:
    FIREBASE_SDK_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.error("Firebase Admin SDK not available. Please install: pip install firebase-admin")

logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK (will be initialized once)
_firebase_app = None


def get_firebase_app():
    """
    Initialize and return Firebase app instance using service account JSON file.
    
    Requires FIREBASE_CREDENTIALS_PATH to be set in .env pointing to your service account JSON file.
    """
    global _firebase_app
    if _firebase_app is None:
        try:
            # Check if Firebase is already initialized
            if not firebase_admin._apps:
                import os
                
                # Get project ID from settings
                project_id = getattr(settings, 'FIREBASE_PROJECT_ID', None)
                if not project_id:
                    raise ValueError("FIREBASE_PROJECT_ID must be set in settings.py")
                
                # Get credentials file path from settings
                cred_path = getattr(settings, 'FIREBASE_CREDENTIALS_PATH', None)
                logger.info(f"checking firebase path {cred_path}")
                if not cred_path:
                    raise ValueError("FIREBASE_CREDENTIALS_PATH must be set in .env file pointing to your service account JSON file")
                
                if not os.path.exists(cred_path):
                    raise FileNotFoundError(f"Firebase credentials file not found at: {cred_path}")
                
                # Load and initialize Firebase with service account JSON file
                cred = credentials.Certificate(cred_path)
                _firebase_app = initialize_app(cred, {'projectId': project_id})
                logger.info(f"Firebase initialized successfully using credentials file for project: {project_id}")
            else:
                _firebase_app = firebase_admin.get_app()
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"Failed to initialize Firebase: {str(e)}")
            logger.error(f"Error details: {error_details}")
            logger.error("Troubleshooting steps:")
            logger.error("1. Set FIREBASE_CREDENTIALS_PATH in .env to point to your service account JSON file")
            logger.error("2. Verify FIREBASE_PROJECT_ID in settings.py (should be 'mgask-2025')")
            logger.error("3. Ensure the JSON file exists and is readable")
            logger.error("4. Test: python manage.py shell -> from apps.notifications.services import get_firebase_app")
            # Don't raise - allow the app to continue without Firebase
            # Notifications will be logged but not sent
            _firebase_app = None
    return _firebase_app


class NotificationService:
    """Service for sending push notifications via Firebase Cloud Messaging"""
    
    @staticmethod
    def send_notification(
        user,
        title: str,
        body: str,
        notification_type: str,
        category: str,
        data: Optional[Dict] = None,
        priority: str = 'high'
    ) -> bool:
        """
        Send push notification to a user
        
        Args:
            user: User instance to send notification to
            title: Notification title
            body: Notification body/message
            notification_type: Type of notification (ORDER_STATUS, PAYMENT, etc.)
            category: Notification category (e.g., order_confirmed)
            data: Additional data payload
            priority: Notification priority (high, normal)
        
        Returns:
            bool: True if notification was sent successfully, False otherwise
        """
        try:
            # Detect user's language preference
            # Check if user has language preference (you can add this to user model later)
            user_language = 'ar'  # Default to Arabic
            if hasattr(user, 'language_preference'):
                user_language = user.language_preference
            
            # Translate title and body to user's language
            translated_title = translate_message(title, user_language, **data) if data else translate_message(title, user_language)
            translated_body = translate_message(body, user_language, **data) if data else translate_message(body, user_language)
            
            # Initialize Firebase Admin SDK
            if not FIREBASE_SDK_AVAILABLE:
                logger.error("Firebase Admin SDK not available. Please install: pip install firebase-admin")
                NotificationLog.objects.create(
                    user=user,
                    notification_type=notification_type,
                    category=category,
                    title=title,
                    body=body,
                    data=data or {},
                    status='failed',
                    error_message="Firebase Admin SDK not installed.",
                )
                return False
            
            firebase_app = get_firebase_app()
            if firebase_app is None:
                logger.warning(f"Firebase not configured - notification logged only for user {user.id}")
                NotificationLog.objects.create(
                    user=user,
                    notification_type=notification_type,
                    category=category,
                    title=title,
                    body=body,
                    data=data or {},
                    status='pending',
                    error_message="Firebase not configured. Set FIREBASE_CREDENTIALS_PATH in .env to point to your service account JSON file.",
                )
                return True  # Return True because notification was logged successfully
            
            # Get active FCM tokens for the user
            fcm_tokens = FCMDeviceToken.objects.filter(
                user=user,
                is_active=True
            )
            
            if not fcm_tokens.exists():
                logger.warning(f"No active FCM tokens found for user {user.id}")
                return False
            
            success_count = 0
            failed_tokens = []
            
            # Build data payload
            payload_data = {
                'type': notification_type,
                'category': category,
                'title': title,
                'body': body,
            }
            
            if data:
                # Add custom data (convert to strings for FCM)
                for key, value in data.items():
                    payload_data[str(key)] = str(value)
            
            for fcm_token in fcm_tokens:
                try:
                    # Build notification payload with translated text
                    notification = messaging.Notification(
                        title=translated_title,
                        body=translated_body
                    )
                    
                    # Build message
                    message = messaging.Message(
                        notification=notification,
                        data=payload_data,
                        token=fcm_token.token,
                        android=messaging.AndroidConfig(
                            priority='high' if priority == 'high' else 'normal',
                            notification=messaging.AndroidNotification(
                                sound='default',
                                priority='high' if priority == 'high' else 'default',
                            )
                        ),
                        apns=messaging.APNSConfig(
                            payload=messaging.APNSPayload(
                                aps=messaging.Aps(
                                    sound='default',
                                    badge=1,
                                )
                            )
                        )
                    )
                    
                    # Send notification using Firebase Admin SDK
                    response = messaging.send(message, app=firebase_app)
                    logger.info(f"Successfully sent notification to user {user.id}, token {fcm_token.id}: {response}")
                    
                    # Log successful notification
                    NotificationLog.objects.create(
                        user=user,
                        fcm_token=fcm_token,
                        notification_type=notification_type,
                        category=category,
                        title=translated_title,
                        body=translated_body,
                        data=data or {},
                        status='sent',
                        sent_at=timezone.now()
                    )
                    
                    success_count += 1
                    
                except messaging.UnregisteredError:
                    # Token is invalid, mark as inactive
                    logger.warning(f"FCM token {fcm_token.id} is unregistered, marking as inactive")
                    fcm_token.is_active = False
                    fcm_token.save()
                    failed_tokens.append(fcm_token)
                    
                except Exception as e:
                    logger.error(f"Failed to send notification to token {fcm_token.id}: {str(e)}")
                    
                    # Log failed notification
                    NotificationLog.objects.create(
                        user=user,
                        fcm_token=fcm_token,
                        notification_type=notification_type,
                        category=category,
                        title=title,
                        body=body,
                        data=data or {},
                        status='failed',
                        error_message=str(e),
                        sent_at=timezone.now()
                    )
                    
                    failed_tokens.append(fcm_token)
            
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Error in send_notification for user {user.id}: {str(e)}")
            return False
    
    @staticmethod
    def send_bulk_notifications(
        users: List,
        title: str,
        body: str,
        notification_type: str,
        category: str,
        data: Optional[Dict] = None,
        priority: str = 'high'
    ) -> Dict:
        """
        Send push notifications to multiple users
        
        Returns:
            Dict with success_count and failed_count
        """
        results = {'success_count': 0, 'failed_count': 0}
        
        for user in users:
            if NotificationService.send_notification(
                user=user,
                title=title,
                body=body,
                notification_type=notification_type,
                category=category,
                data=data,
                priority=priority
            ):
                results['success_count'] += 1
            else:
                results['failed_count'] += 1
        
        return results
    
    @staticmethod
    def send_order_status_notification(order, old_status: str, new_status: str, changed_by):
        """Send notification when order status changes"""
        from apps.orders.models import Order
        
        # Map status to notification messages
        status_messages = {
            'pending': {
                'customer': 'Your order #{order_number} has been placed successfully',
                'tailor': 'New order #{order_number} received from {customer_name}',
            },
            'confirmed': {
                'customer': 'Tailor has accepted your order #{order_number}',
                'tailor': 'You have confirmed order #{order_number}',
            },
            'in_progress': {
                'customer': 'Your order #{order_number} is now in progress',
                'tailor': 'Order #{order_number} is now in progress',
                'rider': 'Order #{order_number} is now in progress',
            },
            'measuring': {
                'customer': 'Rider is on the way to take your measurements for order #{order_number}',
                'rider': 'Please take measurements for order #{order_number}',
            },
            'cutting': {
                'customer': 'Fabric cutting has started for your order #{order_number}',
                'tailor': 'Order #{order_number} is ready for cutting',
            },
            'stitching': {
                'customer': 'Your garment is being stitched for order #{order_number}',
                'tailor': 'Order #{order_number} is ready for stitching',
            },
            'ready_for_delivery': {
                'customer': 'Your order #{order_number} is ready for delivery',
                'tailor': 'Order #{order_number} is ready for pickup',
                'rider': 'Order #{order_number} is ready for pickup from tailor',
            },
            'ready_for_pickup': {
                'customer': 'Your order #{order_number} is ready for pickup at the shop',
                'tailor': 'Order #{order_number} is ready for customer pickup',
            },
            'delivered': {
                'customer': 'Your order #{order_number} has been delivered',
                'tailor': 'Order #{order_number} has been delivered to customer',
                'rider': 'Order #{order_number} delivery completed',
            },
            'collected': {
                'customer': 'Thank you for collecting your order #{order_number}!',
                'tailor': 'Order #{order_number} has been collected by customer',
            },
            'cancelled': {
                'customer': 'Your order #{order_number} has been cancelled',
                'tailor': 'Order #{order_number} has been cancelled by customer',
                'rider': 'Order #{order_number} has been cancelled',
            },
        }
        
        order_number = order.order_number
        customer_name = order.customer.username if order.customer else 'Customer'
        
        # Notify customer
        if order.customer and new_status in status_messages:
            message_template = status_messages[new_status].get('customer', '')
            if message_template:
                NotificationService.send_notification(
                    user=order.customer,
                    title='Order #{order_number} Update',
                    body=message_template,
                    notification_type='ORDER_STATUS',
                    category=f'order_{new_status}',
                    data={
                        'order_id': order.id,
                        'order_number': order_number,
                        'status': new_status,
                        'old_status': old_status,
                        'customer_name': customer_name,
                    },
                    priority='high'
                )
        
        # Notify tailor
        if order.tailor and new_status in status_messages:
            message_template = status_messages[new_status].get('tailor', '')
            if message_template:
                NotificationService.send_notification(
                    user=order.tailor,
                    title='Order #{order_number} Update',
                    body=message_template,
                    notification_type='ORDER_STATUS',
                    category=f'order_{new_status}',
                    data={
                        'order_id': order.id,
                        'order_number': order_number,
                        'status': new_status,
                        'old_status': old_status,
                        'customer_name': customer_name,
                    },
                    priority='high'
                )
        
        # Notify rider
        if order.rider and new_status in status_messages:
            message_template = status_messages[new_status].get('rider', '')
            if message_template:
                NotificationService.send_notification(
                    user=order.rider,
                    title='Order #{order_number} Update',
                    body=message_template,
                    notification_type='ORDER_STATUS',
                    category=f'order_{new_status}',
                    data={
                        'order_id': order.id,
                        'order_number': order_number,
                        'status': new_status,
                        'old_status': old_status,
                        'customer_name': customer_name,
                    },
                    priority='high'
                )
    
    @staticmethod
    def send_tailor_status_notification(order, old_tailor_status: str, new_tailor_status: str, changed_by):
        """Send notification when tailor_status changes"""
        order_number = order.order_number
        customer_name = order.customer.username if order.customer else 'Customer'
        
        # Map tailor_status to notification messages
        tailor_status_messages = {
            'accepted': {
                'customer': 'Tailor has accepted your order #{order_number}',
                'tailor': 'You have accepted order #{order_number}',
                'rider': 'Order #{order_number} has been accepted by tailor and is ready for pickup',
            },
            'in_progress': {
                'customer': 'Tailor is working on your order #{order_number}',
                'tailor': 'You have marked order #{order_number} as in progress',
                'rider': 'Order #{order_number} is now in progress',
            },
            'stitching_started': {
                'customer': 'Tailor has started stitching your garment for order #{order_number}',
                'tailor': 'You have started stitching order #{order_number}',
                'rider': 'Stitching has started for order #{order_number}',
            },
            'stitched': {
                'customer': 'Your garment stitching is complete for order #{order_number}',
                'tailor': 'Stitching completed for order #{order_number}',
                'rider': 'Order #{order_number} stitching is complete and ready for pickup',
            },
            'measurements_complete': {
                'customer': 'Your measurements have been completed for order #{order_number}. Your order is ready for pickup.',
                'tailor': 'Measurements completed for order #{order_number}. Order is ready for customer pickup.',
            },
        }
        
        # Notify customer
        if order.customer and new_tailor_status in tailor_status_messages:
            message_template = tailor_status_messages[new_tailor_status].get('customer', '')
            if message_template:
                NotificationService.send_notification(
                    user=order.customer,
                    title='Order #{order_number} Update',
                    body=message_template,
                    notification_type='ORDER_STATUS',
                    category=f'tailor_{new_tailor_status}',
                    data={
                        'order_id': order.id,
                        'order_number': order_number,
                        'tailor_status': new_tailor_status,
                        'old_tailor_status': old_tailor_status,
                        'status': order.status,
                        'customer_name': customer_name,
                    },
                    priority='high'
                )
        
        # Notify tailor
        if order.tailor and new_tailor_status in tailor_status_messages:
            message_template = tailor_status_messages[new_tailor_status].get('tailor', '')
            if message_template:
                NotificationService.send_notification(
                    user=order.tailor,
                    title='Order #{order_number} Update',
                    body=message_template,
                    notification_type='ORDER_STATUS',
                    category=f'tailor_{new_tailor_status}',
                    data={
                        'order_id': order.id,
                        'order_number': order_number,
                        'tailor_status': new_tailor_status,
                        'old_tailor_status': old_tailor_status,
                        'status': order.status,
                        'customer_name': customer_name,
                    },
                    priority='high'
                )
        
       
        if new_tailor_status == 'accepted':
            NotificationService.send_new_order_broadcast(order, assigned_rider_id=order.assigned_rider_id)
            
        # Notify rider
        if order.rider and new_tailor_status in tailor_status_messages:
            message_template = tailor_status_messages[new_tailor_status].get('rider', '')
            if message_template:
                NotificationService.send_notification(
                    user=order.rider,
                    title='Order #{order_number} Update',
                    body=message_template,
                    notification_type='ORDER_STATUS',
                    category=f'tailor_{new_tailor_status}',
                    data={
                        'order_id': order.id,
                        'order_number': order_number,
                        'tailor_status': new_tailor_status,
                        'old_tailor_status': old_tailor_status,
                        'status': order.status,
                        'customer_name': customer_name,
                    },
                    priority='high'
                )
    
    @staticmethod
    def send_rider_status_notification(order, old_rider_status: str, new_rider_status: str, changed_by):
        """Send notification when rider_status changes"""
        order_number = order.order_number
        customer_name = order.customer.username if order.customer else 'Customer'
        rider_name = order.rider.rider_profile.full_name if hasattr(order.rider, 'rider_profile') and order.rider.rider_profile else order.rider.username if order.rider else 'Rider'
        
        # Determine if this is a measurement service order
        is_measurement_order = order.order_type == 'measurement_service'
        
        # Map rider_status to notification messages
        rider_status_messages = {
            'accepted': {
                'customer': 'Rider has accepted your order #{order_number}',
                'tailor': 'Rider has accepted order #{order_number}',
                'rider': 'You have accepted order #{order_number}',
            },
            'on_way_to_measurement': {
                'customer': 'Rider is on the way to take your measurements for order #{order_number}',
                'tailor': 'Rider is on the way to customer for measurements - order #{order_number}',
                'rider': 'You are on the way to take measurements for order #{order_number}',
            },
            'measuring': {
                'customer': 'Rider is taking your measurements now for order #{order_number}',
                'tailor': 'Rider is currently taking customer measurements - order #{order_number}',
                'rider': 'Measurements in progress for order #{order_number}',
            },
            'measurement_taken': {
                'customer': 'Your measurements have been completed for order #{order_number}' if is_measurement_order else 'Your measurements have been completed for order #{order_number}. Tailor will now start stitching.',
                'tailor': 'Measurements ready for order #{order_number}' if is_measurement_order else 'Measurements ready for order #{order_number}. You can now start stitching.',
                'rider': 'Measurements successfully recorded for order #{order_number}',
            },
            'on_way_to_pickup': {
                'customer': 'Rider is on the way to pickup your order #{order_number} from tailor',
                'tailor': 'Rider is on the way to pickup order #{order_number}',
                'rider': 'You are on the way to pickup order #{order_number} from tailor',
            },
            'picked_up': {
                'customer': 'Rider has picked up your order #{order_number} and is preparing for delivery',
                'tailor': 'Rider has picked up order #{order_number}',
                'rider': 'You have picked up order #{order_number} from tailor',
            },
            'on_way_to_delivery': {
                'customer': 'Your order #{order_number} is on the way! Rider will arrive soon.',
                'tailor': 'Order #{order_number} is now out for delivery',
                'rider': 'You are delivering order #{order_number} to customer',
            },
            'delivered': {
                'customer': 'Your order #{order_number} has been delivered successfully',
                'tailor': 'Order #{order_number} has been delivered to customer',
                'rider': 'Order #{order_number} delivery completed',
            },
        }
        
        # Notify customer
        if order.customer and new_rider_status in rider_status_messages:
            message_template = rider_status_messages[new_rider_status].get('customer', '')
            if message_template:
                NotificationService.send_notification(
                    user=order.customer,
                    title='Order #{order_number} Update',
                    body=message_template,
                    notification_type='ORDER_STATUS',
                    category=f'rider_{new_rider_status}',
                    data={
                        'order_id': order.id,
                        'order_number': order_number,
                        'rider_status': new_rider_status,
                        'old_rider_status': old_rider_status,
                        'status': order.status,
                    },
                    priority='high'
                )
        
        # Notify tailor (if assigned)
        if order.tailor and new_rider_status in rider_status_messages:
            message_template = rider_status_messages[new_rider_status].get('tailor', '')
            if message_template:
                NotificationService.send_notification(
                    user=order.tailor,
                    title='Order #{order_number} Update',
                    body=message_template,
                    notification_type='ORDER_STATUS',
                    category=f'rider_{new_rider_status}',
                    data={
                        'order_id': order.id,
                        'order_number': order_number,
                        'rider_status': new_rider_status,
                        'old_rider_status': old_rider_status,
                        'status': order.status,
                    },
                    priority='high'
                )
        
        # Notify rider
        if order.rider and new_rider_status in rider_status_messages:
            message_template = rider_status_messages[new_rider_status].get('rider', '')
            if message_template:
                NotificationService.send_notification(
                    user=order.rider,
                    title='Order #{order_number} Update',
                    body=message_template,
                    notification_type='ORDER_STATUS',
                    category=f'rider_{new_rider_status}',
                    data={
                        'order_id': order.id,
                        'order_number': order_number,
                        'rider_status': new_rider_status,
                        'old_rider_status': old_rider_status,
                        'status': order.status,
                    },
                    priority='high'
                )
    
    @staticmethod
    def send_payment_status_notification(order, old_status: str, new_status: str):
        """Send notification when payment status changes"""
        order_number = order.order_number
        customer_name = order.customer.username if order.customer else "Customer"
        total_amount = str(order.total_amount)
        
        payment_messages = {
            'paid': {
                'customer': 'Your order #{order_number} has been placed successfully! Payment of SAR {total_amount} confirmed.',
                'tailor': 'New order #{order_number} received from {customer}. Payment of SAR {total_amount} confirmed.',
            },
            'pending': {
                'customer': 'Payment pending for order #{order_number}',
            },
            'refunded': {
                'customer': 'Refund of SAR {total_amount} has been processed for order #{order_number}',
                'tailor': 'Refund issued for order #{order_number}',
            },
        }
        
        # Notify customer
        if order.customer and new_status in payment_messages:
            message_template = payment_messages[new_status].get('customer', '')
            if message_template:
                NotificationService.send_notification(
                    user=order.customer,
                    title='Payment Update',
                    body=message_template,
                    notification_type='PAYMENT',
                    category=f'payment_{new_status}',
                    data={
                        'order_id': order.id,
                        'order_number': order_number,
                        'payment_status': new_status,
                        'old_payment_status': old_status,
                        'total_amount': total_amount,
                    },
                    priority='high'
                )
        
        # Notify tailor
        if order.tailor and new_status in payment_messages:
            message_template = payment_messages[new_status].get('tailor', '')
            if message_template:
                NotificationService.send_notification(
                    user=order.tailor,
                    title='Payment Update',
                    body=message_template,
                    notification_type='PAYMENT',
                    category=f'payment_{new_status}',
                    data={
                        'order_id': order.id,
                        'order_number': order_number,
                        'payment_status': new_status,
                        'old_payment_status': old_status,
                        'customer': customer_name,
                        'total_amount': total_amount,
                    },
                    priority='high'
                )
    
    @staticmethod
    def send_rider_assignment_notification(order, rider):
        """Send notification when rider is assigned to an order"""
        order_number = order.order_number
        rider_name = rider.rider_profile.full_name if hasattr(rider, 'rider_profile') and rider.rider_profile else rider.username
        
        # Notify customer
        if order.customer:
            NotificationService.send_notification(
                user=order.customer,
                title='Rider Assigned',
                body='Rider {rider_name} has been assigned to deliver your order #{order_number}',
                notification_type='RIDER_ASSIGNMENT',
                category='rider_assigned',
                data={
                    'order_id': order.id,
                    'order_number': order_number,
                    'rider_id': rider.id,
                    'rider_name': rider_name,
                },
                priority='high'
            )
        
        # Notify tailor
        if order.tailor:
            NotificationService.send_notification(
                user=order.tailor,
                title='Rider Assigned',
                body='Rider {rider_name} will pick up order #{order_number}',
                notification_type='RIDER_ASSIGNMENT',
                category='rider_assigned',
                data={
                    'order_id': order.id,
                    'order_number': order_number,
                    'rider_id': rider.id,
                    'rider_name': rider_name,
                },
                priority='high'
            )
        
        # Notify rider
        NotificationService.send_notification(
            user=rider,
            title='New Order Assignment',
            body='You have been assigned to order #{order_number}',
            notification_type='RIDER_ASSIGNMENT',
            category='order_assigned',
            data={
                'order_id': order.id,
                'order_number': order_number,
            },
            priority='high'
        )
    
    @staticmethod
    def send_measurement_taken_notification(order, rider):
        """Send notification when rider takes measurements for fabric_with_stitching orders"""
        order_number = order.order_number
        rider_name = rider.rider_profile.full_name if hasattr(rider, 'rider_profile') and rider.rider_profile else rider.username
        customer_name = order.customer.get_full_name() if order.customer else order.customer.username if order.customer else 'Customer'
        
        # Determine if this is a measurement service order
        is_measurement_order = order.order_type == 'measurement_service'
        
        # Notify customer
        if order.customer:
            if is_measurement_order:
                # Measurement service - no stitching
                body = 'Your measurements have been completed for order #{order_number}. Thank you!'
            else:
                # Fabric with stitching - mention stitching
                body = 'Measurements have been taken for your order #{order_number}. Tailor will now start stitching.'
            
            NotificationService.send_notification(
                user=order.customer,
                title='Measurements Taken',
                body=body,
                notification_type='ORDER_STATUS',
                category='measurement_taken',
                data={
                    'order_id': order.id,
                    'order_number': order_number,
                    'rider_id': rider.id,
                    'rider_name': rider_name,
                },
                priority='high'
            )
        
        # Notify tailor - IMPORTANT: This tells tailor they can now start stitching
        if order.tailor:
            if is_measurement_order:
                # Measurement service - no stitching needed
                body = 'Measurements have been completed for order #{order_number}.'
            else:
                # Fabric with stitching - can start stitching
                body = 'Measurements have been taken for order #{order_number}. You can now start stitching.'
            
            NotificationService.send_notification(
                user=order.tailor,
                title='Measurements Ready',
                body=body,
                notification_type='ORDER_STATUS',
                category='measurement_taken',
                data={
                    'order_id': order.id,
                    'order_number': order_number,
                    'customer_name': customer_name,
                    'rider_id': rider.id,
                    'rider_name': rider_name,
                },
                priority='high'
            )

        
        # Notify rider (confirmation)
        if is_measurement_order:
            body = 'Measurements successfully recorded for order #{order_number}.'
        else:
            body = 'Measurements successfully recorded for order #{order_number}. Waiting for tailor to complete stitching.'
        
        NotificationService.send_notification(
            user=rider,
            title='Measurements Recorded',
            body=body,
            notification_type='ORDER_STATUS',
            category='measurement_taken',
            data={
                'order_id': order.id,
                'order_number': order_number,
            },
            priority='normal'
        )

    @staticmethod
    def send_new_order_broadcast(order, assigned_rider_id=None):
        """
        Send notification to riders when order is accepted by tailor.
        
        Args:
            order: Order instance
            assigned_rider_id: If provided, only notify this specific rider.
                              If None, broadcast to all available riders.
        """
        from apps.accounts.models import CustomUser
        import logging
        
        logger = logging.getLogger(__name__)
        
        if assigned_rider_id:
            # Specific rider assignment - send targeted notification
            try:
                assigned_rider = CustomUser.objects.get(
                    id=assigned_rider_id,
                    role='RIDER',
                    is_active=True,
                    rider_profile__review__review_status='approved',
                    rider_profile__is_available=True
                )
                
                # Send notification to only this rider
                success = NotificationService.send_notification(
                    user=assigned_rider,
                    title=f"New order #{order.order_number} assigned to you",
                    body="You have been specifically assigned to this order by the tailor",
                    notification_type='ORDER_ASSIGNMENT',
                    category='order_assigned',
                    data={
                        'order_id': order.id,
                        'order_number': order.order_number,
                        'assigned': True
                    },
                    priority='high'
                )
                
                if success:
                    logger.info(f"Order {order.order_number} assigned to rider {assigned_rider.id}")
                else:
                    logger.warning(f"Failed to notify assigned rider {assigned_rider.id} for order {order.order_number}")
                
                return  # Don't broadcast if specific rider assigned
                
            except CustomUser.DoesNotExist:
                logger.warning(f"Assigned rider {assigned_rider_id} not found or not eligible. Falling back to broadcast.")
                # Fall through to broadcast
        
        # No specific assignment or assigned rider not available - broadcast to all
        active_riders = CustomUser.objects.filter(
            role='RIDER',
            is_active=True,
            rider_profile__review__review_status='approved',
            rider_profile__is_available=True
        ).distinct()
        
        if not active_riders.exists():
            logger.info("No active riders found for broadcast")
            return
            
        order_number = order.order_number
        title = "New available order #{order_number}"
        body = "A new order is available for pickup. Check your available orders list."
        
        if FIREBASE_SDK_AVAILABLE:
            count = 0
            for rider in active_riders:
                success = NotificationService.send_notification(
                    user=rider,
                    title=title,
                    body=body,
                    notification_type='ORDER_AVAILABLE',
                    category='new_order_available',
                    data={
                        'order_id': order.id,
                        'order_number': order_number,
                        'broadcast': True
                    },
                    priority='high'
                )
                if success:
                    count += 1
            
            logger.info(f"Broadcast sent to {count} riders for order {order_number}")


