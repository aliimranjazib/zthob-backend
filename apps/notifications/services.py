import logging
from typing import List, Dict, Optional
from django.conf import settings
from django.utils import timezone
from firebase_admin import messaging, credentials, initialize_app
import firebase_admin
from .models import FCMDeviceToken, NotificationLog

logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK (will be initialized once)
_firebase_app = None


def get_firebase_app():
    """
    Initialize and return Firebase app instance
    
    Supports multiple authentication methods:
    1. Credentials file (FIREBASE_CREDENTIALS_PATH)
    2. Application Default Credentials (ADC) - for GCP environments
    3. Environment variables (GOOGLE_APPLICATION_CREDENTIALS)
    
    If service account key creation is restricted, use Application Default Credentials
    by running: gcloud auth application-default login
    """
    global _firebase_app
    if _firebase_app is None:
        try:
            # Check if Firebase is already initialized
            if not firebase_admin._apps:
                import os
                # Get project ID from multiple sources (priority order)
                project_id = None
                
                # 1. Try from settings
                project_id = getattr(settings, 'FIREBASE_PROJECT_ID', None)
                
                # 2. Try from environment variables
                if not project_id:
                    project_id = os.environ.get('GOOGLE_CLOUD_PROJECT') or os.environ.get('FIREBASE_PROJECT_ID')
                
                # 3. If on GCP, try to get from metadata server
                if not project_id:
                    try:
                        import urllib.request
                        req = urllib.request.Request(
                            'http://169.254.169.254/computeMetadata/v1/project/project-id',
                            headers={'Metadata-Flavor': 'Google'}
                        )
                        project_id = urllib.request.urlopen(req, timeout=2).read().decode('utf-8')
                        logger.info(f"Got project ID from GCP metadata server: {project_id}")
                    except:
                        pass
                
                if not project_id:
                    raise ValueError("FIREBASE_PROJECT_ID must be set in settings.py, GOOGLE_CLOUD_PROJECT environment variable, or available from GCP metadata server")
                
                # Set GOOGLE_CLOUD_PROJECT environment variable for Firebase SDK
                if not os.environ.get('GOOGLE_CLOUD_PROJECT'):
                    os.environ['GOOGLE_CLOUD_PROJECT'] = project_id
                    logger.info(f"Set GOOGLE_CLOUD_PROJECT environment variable to: {project_id}")
                
                # Method 1: Try credentials file path (service account JSON)
                cred_path = getattr(settings, 'FIREBASE_CREDENTIALS_PATH', None)
                if cred_path and os.path.exists(cred_path):
                    cred = credentials.Certificate(cred_path)
                    _firebase_app = initialize_app(cred, {'projectId': project_id})
                    logger.info(f"Firebase initialized using credentials file for project: {project_id}")
                else:
                    # Method 2: Try ADC credentials file explicitly
                    # Check standard ADC location and set environment variable
                    adc_path = os.path.expanduser('~/.config/gcloud/application_default_credentials.json')
                    if os.path.exists(adc_path) and not os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
                        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = adc_path
                        logger.info(f"Found ADC credentials at {adc_path}, setting GOOGLE_APPLICATION_CREDENTIALS")
                    
                    # Method 3: Use Application Default Credentials (ADC)
                    # This works when:
                    # - Running on Google Cloud (Cloud Run, App Engine, Compute Engine)
                    # - Using gcloud auth application-default login (local dev)
                    # - Service account is attached to the instance
                    # IMPORTANT: Must specify projectId when using ADC
                    # Also set GOOGLE_CLOUD_PROJECT to ensure Firebase SDK can access it
                    firebase_config = {'projectId': project_id}
                    _firebase_app = initialize_app(firebase_config)
                    logger.info(f"Firebase initialized using Application Default Credentials for project: {project_id}")
            else:
                _firebase_app = firebase_admin.get_app()
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"Failed to initialize Firebase: {str(e)}")
            logger.error(f"Error details: {error_details}")
            logger.error("Troubleshooting steps:")
            logger.error("1. Verify Application Default Credentials: gcloud auth application-default login")
            logger.error("2. Verify project: gcloud config set project mgask-2025")
            logger.error("3. Check FIREBASE_PROJECT_ID in settings.py (should be 'mgask-2025')")
            logger.error("4. Test: python manage.py shell -> from apps.notifications.services import get_firebase_app")
            logger.error("5. Or use Firebase REST API with FIREBASE_SERVER_KEY (see FIREBASE_SETUP_ALTERNATIVES.md)")
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
            # Initialize Firebase if not already done
            firebase_app = get_firebase_app()
            if firebase_app is None:
                # Firebase not initialized - log notification but don't send
                logger.warning(f"Firebase not initialized - notification logged only for user {user.id}")
                NotificationLog.objects.create(
                    user=user,
                    notification_type=notification_type,
                    category=category,
                    title=title,
                    body=body,
                    data=data or {},
                    status='pending',
                    error_message="Firebase not initialized - logged only. See FIREBASE_SETUP_ALTERNATIVES.md",
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
            
            for fcm_token in fcm_tokens:
                try:
                    # Build notification payload
                    notification = messaging.Notification(
                        title=title,
                        body=body
                    )
                    
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
                    
                    # Send notification
                    response = messaging.send(message)
                    logger.info(f"Successfully sent notification to user {user.id}, token {fcm_token.id}: {response}")
                    
                    # Log successful notification
                    NotificationLog.objects.create(
                        user=user,
                        fcm_token=fcm_token,
                        notification_type=notification_type,
                        category=category,
                        title=title,
                        body=body,
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
            'delivered': {
                'customer': 'Your order #{order_number} has been delivered',
                'tailor': 'Order #{order_number} has been delivered to customer',
                'rider': 'Order #{order_number} delivery completed',
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
                title = f"Order #{order_number} Update"
                body = message_template.format(
                    order_number=order_number,
                    customer_name=customer_name
                )
                
                NotificationService.send_notification(
                    user=order.customer,
                    title=title,
                    body=body,
                    notification_type='ORDER_STATUS',
                    category=f'order_{new_status}',
                    data={
                        'order_id': order.id,
                        'order_number': order_number,
                        'status': new_status,
                        'old_status': old_status,
                    },
                    priority='high'
                )
        
        # Notify tailor
        if order.tailor and new_status in status_messages:
            message_template = status_messages[new_status].get('tailor', '')
            if message_template:
                title = f"Order #{order_number} Update"
                body = message_template.format(
                    order_number=order_number,
                    customer_name=customer_name
                )
                
                NotificationService.send_notification(
                    user=order.tailor,
                    title=title,
                    body=body,
                    notification_type='ORDER_STATUS',
                    category=f'order_{new_status}',
                    data={
                        'order_id': order.id,
                        'order_number': order_number,
                        'status': new_status,
                        'old_status': old_status,
                    },
                    priority='high'
                )
        
        # Notify rider
        if order.rider and new_status in status_messages:
            message_template = status_messages[new_status].get('rider', '')
            if message_template:
                title = f"Order #{order_number} Update"
                body = message_template.format(
                    order_number=order_number,
                    customer_name=customer_name
                )
                
                NotificationService.send_notification(
                    user=order.rider,
                    title=title,
                    body=body,
                    notification_type='ORDER_STATUS',
                    category=f'order_{new_status}',
                    data={
                        'order_id': order.id,
                        'order_number': order_number,
                        'status': new_status,
                        'old_status': old_status,
                    },
                    priority='high'
                )
    
    @staticmethod
    def send_payment_status_notification(order, old_status: str, new_status: str):
        """Send notification when payment status changes"""
        order_number = order.order_number
        
        payment_messages = {
            'paid': {
                'customer': f'Payment of ${order.total_amount} received for order #{order_number}',
                'tailor': f'Payment received for order #{order_number} - ${order.total_amount}',
            },
            'pending': {
                'customer': f'Payment pending for order #{order_number}',
            },
            'refunded': {
                'customer': f'Refund of ${order.total_amount} has been processed for order #{order_number}',
                'tailor': f'Refund issued for order #{order_number}',
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
                        'amount': str(order.total_amount),
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
                        'amount': str(order.total_amount),
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
                body=f'Rider {rider_name} has been assigned to deliver your order #{order_number}',
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
                body=f'Rider {rider_name} will pick up order #{order_number}',
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
            body=f'You have been assigned to order #{order_number}',
            notification_type='RIDER_ASSIGNMENT',
            category='order_assigned',
            data={
                'order_id': order.id,
                'order_number': order_number,
            },
            priority='high'
        )

