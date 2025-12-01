import logging
import requests
from typing import List, Dict, Optional, Tuple
from django.conf import settings
from django.utils import timezone
from .models import FCMDeviceToken, NotificationLog

# Try to import Firebase Admin SDK (optional - only if using SDK method)
try:
    from firebase_admin import messaging, credentials, initialize_app
    import firebase_admin
    FIREBASE_SDK_AVAILABLE = True
except ImportError:
    FIREBASE_SDK_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.info("Firebase Admin SDK not available - using REST API only")

logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK (will be initialized once) - only if using SDK
_firebase_app = None

# FCM REST API endpoint
FCM_LEGACY_API_URL = "https://fcm.googleapis.com/fcm/send"

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
                # Get project ID from settings or environment variable
                project_id = getattr(settings, 'FIREBASE_PROJECT_ID', None) or os.environ.get('GOOGLE_CLOUD_PROJECT') or os.environ.get('FIREBASE_PROJECT_ID')
                
                if not project_id:
                    raise ValueError("FIREBASE_PROJECT_ID must be set in settings.py or GOOGLE_CLOUD_PROJECT environment variable")
                
                # Method 1: Try credentials file path (service account JSON or Workload Identity)
                cred_path = getattr(settings, 'FIREBASE_CREDENTIALS_PATH', None)
                if cred_path and os.path.exists(cred_path):
                    # Check if it's a Workload Identity credentials file
                    try:
                        import json
                        with open(cred_path, 'r') as f:
                            cred_data = json.load(f)
                            if cred_data.get('type') == 'external_account':
                                # Workload Identity Federation credentials
                                from google.auth import load_credentials_from_file
                                cred, _ = load_credentials_from_file(
                                    cred_path,
                                    scopes=['https://www.googleapis.com/auth/firebase.messaging']
                                )
                                _firebase_app = initialize_app(cred, {'projectId': project_id})
                                logger.info(f"Firebase initialized using Workload Identity credentials for project: {project_id}")
                            else:
                                # Regular service account JSON
                                cred = credentials.Certificate(cred_path)
                                _firebase_app = initialize_app(cred, {'projectId': project_id})
                                logger.info(f"Firebase initialized using credentials file for project: {project_id}")
                    except Exception as e:
                        logger.error(f"Error loading credentials file: {str(e)}")
                        # Fall through to next method
                else:
                    # Method 2: Try ADC credentials file explicitly
                    # Check standard ADC location and set environment variable
                    adc_path = os.path.expanduser('~/.config/gcloud/application_default_credentials.json')
                    if os.path.exists(adc_path) and not os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
                        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = adc_path
                        logger.info(f"Found ADC credentials at {adc_path}, setting GOOGLE_APPLICATION_CREDENTIALS")
                    
                    # Method 3: Use Application Default Credentials (ADC)
                    # Check if running on GCP first
                    is_gcp = False
                    try:
                        import urllib.request
                        req = urllib.request.Request(
                            'http://169.254.169.254/computeMetadata/v1/instance/id',
                            headers={'Metadata-Flavor': 'Google'}
                        )
                        urllib.request.urlopen(req, timeout=2)
                        is_gcp = True
                        logger.info("Detected GCP environment - will use instance service account")
                    except:
                        is_gcp = False
                    
                    if is_gcp:
                        # On GCP: Clear any user ADC credentials that might interfere
                        if 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
                            adc_file = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
                            if 'application_default_credentials.json' in adc_file:
                                logger.info(f"Clearing user ADC credentials to use instance service account")
                                os.environ.pop('GOOGLE_APPLICATION_CREDENTIALS', None)
                        
                        # Also remove user ADC file if it exists (to force instance service account)
                        adc_path = os.expanduser('~/.config/gcloud/application_default_credentials.json')
                        if os.path.exists(adc_path):
                            logger.info(f"User ADC file exists at {adc_path} - instance service account will be used instead")
                    
                    # Initialize with explicit project ID
                    # On GCP, this will use instance service account automatically
                    # Off GCP, this will use user ADC credentials if available
                    _firebase_app = initialize_app({'projectId': project_id})
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


def send_fcm_via_rest_api(token: str, title: str, body: str, data: Dict = None, priority: str = 'high') -> Tuple[bool, str]:
    """
    Send FCM notification using REST API (Server Key method)
    
    Returns:
        tuple: (success: bool, message: str)
    """
    server_key = getattr(settings, 'FIREBASE_SERVER_KEY', None)
    
    if not server_key:
        return False, "FIREBASE_SERVER_KEY not configured"
    
    # Build payload
    payload = {
        'to': token,
        'notification': {
            'title': title,
            'body': body,
            'sound': 'default',
        },
        'priority': 'high' if priority == 'high' else 'normal',
    }
    
    # Add data payload if provided
    if data:
        # Convert all values to strings (FCM requirement)
        payload['data'] = {str(k): str(v) for k, v in data.items()}
    
    # Add Android-specific config
    payload['android'] = {
        'priority': 'high' if priority == 'high' else 'normal',
        'notification': {
            'sound': 'default',
            'priority': 'high' if priority == 'high' else 'default',
        }
    }
    
    # Add iOS-specific config
    payload['apns'] = {
        'payload': {
            'aps': {
                'sound': 'default',
                'badge': 1,
            }
        }
    }
    
    try:
        headers = {
            'Authorization': f'key={server_key}',
            'Content-Type': 'application/json',
        }
        
        response = requests.post(
            FCM_LEGACY_API_URL,
            json=payload,
            headers=headers,
            timeout=10
        )
        
        response.raise_for_status()
        result = response.json()
        
        # Check response
        if result.get('success') == 1:
            message_id = result.get('results', [{}])[0].get('message_id', 'unknown')
            return True, f"Notification sent successfully. Message ID: {message_id}"
        elif result.get('failure') == 1:
            error = result.get('results', [{}])[0].get('error', 'Unknown error')
            
            # Handle specific errors
            if error == 'InvalidRegistration':
                return False, "InvalidRegistration: Token is invalid or expired"
            elif error == 'NotRegistered':
                return False, "NotRegistered: Token is not registered"
            elif error == 'Unavailable':
                return False, "Unavailable: FCM service temporarily unavailable"
            else:
                return False, f"FCM Error: {error}"
        else:
            return False, f"Unexpected response: {result}"
            
    except requests.exceptions.RequestException as e:
        logger.error(f"FCM REST API request failed: {str(e)}")
        return False, f"Request failed: {str(e)}"
    except Exception as e:
        logger.error(f"FCM REST API error: {str(e)}")
        return False, f"Error: {str(e)}"


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
            # Check which method to use: REST API (preferred) or SDK (fallback)
            server_key = getattr(settings, 'FIREBASE_SERVER_KEY', None)
            use_rest_api = bool(server_key)
            
            if not use_rest_api:
                # Fallback to SDK if Server Key not available
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
                        error_message="Firebase not configured. Set FIREBASE_SERVER_KEY or configure SDK credentials.",
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
                    if use_rest_api:
                        # Method 1: REST API (preferred - no authentication issues)
                        success, message = send_fcm_via_rest_api(
                            token=fcm_token.token,
                            title=title,
                            body=body,
                            data=payload_data,
                            priority=priority
                        )
                        
                        if success:
                            logger.info(f"Successfully sent notification via REST API to user {user.id}, token {fcm_token.id}: {message}")
                            
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
                        else:
                            # Check if token is invalid
                            if 'InvalidRegistration' in message or 'NotRegistered' in message:
                                logger.warning(f"FCM token {fcm_token.id} is invalid, marking as inactive: {message}")
                                fcm_token.is_active = False
                                fcm_token.save()
                                failed_tokens.append(fcm_token)
                            else:
                                logger.error(f"Failed to send notification via REST API to token {fcm_token.id}: {message}")
                                
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
                                    error_message=message,
                                    sent_at=timezone.now()
                                )
                                
                                failed_tokens.append(fcm_token)
                    else:
                        # Method 2: SDK (fallback)
                        if not FIREBASE_SDK_AVAILABLE:
                            logger.error("Firebase SDK not available and FIREBASE_SERVER_KEY not set")
                            failed_tokens.append(fcm_token)
                            continue
                        
                        # Build notification payload
                        notification = messaging.Notification(
                            title=title,
                            body=body
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
                        
                        # Send notification - explicitly use the initialized app
                        response = messaging.send(message, app=firebase_app)
                        logger.info(f"Successfully sent notification via SDK to user {user.id}, token {fcm_token.id}: {response}")
                    
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

