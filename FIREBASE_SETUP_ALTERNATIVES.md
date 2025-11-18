# Firebase Setup - Alternative Methods

## Problem: Service Account Key Creation Restricted

If you see this error:
> "Key creation is not allowed on this service account. Please check if service account key creation is restricted by organization policies."

This means your Google Cloud organization has security policies that prevent downloading service account keys. This is common in enterprise environments.

---

## Solution 1: Use Application Default Credentials (Recommended for Production)

This is the **best practice** for production environments and works when key creation is restricted.

### Setup Steps:

1. **Grant permissions to your service account:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Navigate to IAM & Admin > Service Accounts
   - Find your Firebase service account (usually `firebase-adminsdk-xxxxx@project-id.iam.gserviceaccount.com`)
   - Note the service account email

2. **Use Application Default Credentials:**

   The Firebase Admin SDK will automatically use Application Default Credentials (ADC) if no credentials file is provided.

   **Update `apps/notifications/services.py`:**

   ```python
   def get_firebase_app():
       """Initialize and return Firebase app instance"""
       global _firebase_app
       if _firebase_app is None:
           try:
               # Check if Firebase is already initialized
               if not firebase_admin._apps:
                   # Try to use credentials file first
                   cred_path = getattr(settings, 'FIREBASE_CREDENTIALS_PATH', None)
                   if cred_path and os.path.exists(cred_path):
                       cred = credentials.Certificate(cred_path)
                       _firebase_app = initialize_app(cred)
                   else:
                       # Use Application Default Credentials (ADC)
                       # This works with:
                       # - Google Cloud Run/App Engine (automatic)
                       # - gcloud auth application-default login (local dev)
                       # - Service account attached to VM/instance
                       _firebase_app = initialize_app()
               else:
                   _firebase_app = firebase_admin.get_app()
           except Exception as e:
               logger.error(f"Failed to initialize Firebase: {str(e)}")
               raise
       return _firebase_app
   ```

3. **For Local Development:**

   ```bash
   # Install gcloud CLI if not installed
   # https://cloud.google.com/sdk/docs/install

   # Authenticate with your Google account
   gcloud auth application-default login

   # Set your project
   gcloud config set project YOUR_PROJECT_ID
   ```

4. **For Production (Google Cloud Run/App Engine/Compute Engine):**

   - Attach the service account to your instance/container
   - ADC will automatically use the attached service account
   - No credentials file needed!

---

## Solution 2: Use Environment Variables

Instead of a JSON file, use environment variables.

### Setup Steps:

1. **Get the service account credentials** (if you have access):
   - Service account email
   - Private key (if available)

2. **Set environment variables:**

   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS='{"type":"service_account","project_id":"your-project","private_key_id":"...","private_key":"...","client_email":"...","client_id":"...","auth_uri":"...","token_uri":"...","auth_provider_x509_cert_url":"...","client_x509_cert_url":"..."}'
   ```

   Or set individual variables:

   ```bash
   export FIREBASE_PROJECT_ID="your-project-id"
   export FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
   export FIREBASE_CLIENT_EMAIL="firebase-adminsdk-xxxxx@project.iam.gserviceaccount.com"
   ```

3. **Update `apps/notifications/services.py`:**

   ```python
   import os
   import json
   
   def get_firebase_app():
       global _firebase_app
       if _firebase_app is None:
           try:
               if not firebase_admin._apps:
                   # Method 1: Try credentials file
                   cred_path = getattr(settings, 'FIREBASE_CREDENTIALS_PATH', None)
                   if cred_path and os.path.exists(cred_path):
                       cred = credentials.Certificate(cred_path)
                       _firebase_app = initialize_app(cred)
                   # Method 2: Try environment variable JSON
                   elif os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
                       cred_dict = json.loads(os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'))
                       cred = credentials.Certificate(cred_dict)
                       _firebase_app = initialize_app(cred)
                   # Method 3: Use Application Default Credentials
                   else:
                       _firebase_app = initialize_app()
               else:
                   _firebase_app = firebase_admin.get_app()
           except Exception as e:
               logger.error(f"Failed to initialize Firebase: {str(e)}")
               raise
       return _firebase_app
   ```

---

## Solution 3: Request Admin to Create Key

If you're in an organization, ask your Google Cloud admin to:

1. Create the service account key for you
2. Or grant you permission to create keys
3. Or provide you with the credentials file securely

**What to ask for:**
- Service account JSON key file
- Or permission to create keys for the Firebase service account

---

## Solution 4: Use Firebase REST API (Alternative Approach)

If you can't use Firebase Admin SDK, you can use Firebase REST API directly.

### Update `apps/notifications/services.py`:

```python
import requests
from django.conf import settings

class NotificationService:
    """Service for sending push notifications via Firebase Cloud Messaging REST API"""
    
    @staticmethod
    def send_notification_via_rest_api(
        user,
        title: str,
        body: str,
        notification_type: str,
        category: str,
        data: Optional[Dict] = None,
        priority: str = 'high'
    ) -> bool:
        """
        Send notification using Firebase REST API
        Requires FIREBASE_SERVER_KEY in settings
        """
        try:
            # Get FCM tokens
            fcm_tokens = FCMDeviceToken.objects.filter(
                user=user,
                is_active=True
            )
            
            if not fcm_tokens.exists():
                return False
            
            server_key = getattr(settings, 'FIREBASE_SERVER_KEY', None)
            if not server_key:
                logger.error("FIREBASE_SERVER_KEY not configured")
                return False
            
            url = "https://fcm.googleapis.com/fcm/send"
            headers = {
                "Authorization": f"key={server_key}",
                "Content-Type": "application/json"
            }
            
            success_count = 0
            for fcm_token in fcm_tokens:
                payload = {
                    "to": fcm_token.token,
                    "notification": {
                        "title": title,
                        "body": body
                    },
                    "data": {
                        "type": notification_type,
                        "category": category,
                        **{str(k): str(v) for k, v in (data or {}).items()}
                    },
                    "priority": priority
                }
                
                try:
                    response = requests.post(url, json=payload, headers=headers)
                    if response.status_code == 200:
                        success_count += 1
                        # Log success
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
                    else:
                        # Log failure
                        NotificationLog.objects.create(
                            user=user,
                            fcm_token=fcm_token,
                            notification_type=notification_type,
                            category=category,
                            title=title,
                            body=body,
                            data=data or {},
                            status='failed',
                            error_message=response.text,
                            sent_at=timezone.now()
                        )
                except Exception as e:
                    logger.error(f"Failed to send notification: {str(e)}")
            
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Error sending notification: {str(e)}")
            return False
```

**Get Firebase Server Key:**
1. Go to Firebase Console
2. Project Settings > Cloud Messaging
3. Copy "Server key" (Legacy)

**Add to settings.py:**
```python
FIREBASE_SERVER_KEY = os.environ.get('FIREBASE_SERVER_KEY', 'your-server-key-here')
```

---

## Recommended Approach

**For Development:**
- Use `gcloud auth application-default login` (Solution 1)

**For Production:**
- Use Application Default Credentials with service account attached to instance (Solution 1)
- Or use Firebase REST API with server key (Solution 4)

**For Organizations:**
- Request admin to provide credentials or permissions (Solution 3)
- Or use Application Default Credentials (Solution 1)

---

## Testing Without Credentials

You can test the notification system without Firebase credentials by:

1. **Mock the notification service** in tests
2. **Check notification logs** - notifications will be logged even if Firebase fails
3. **Use a test Firebase project** - Create a separate Firebase project for testing

---

## Quick Fix for Now

If you just want to test locally without Firebase:

1. **Comment out Firebase initialization** temporarily
2. **Notifications will be logged** but not sent
3. **Check notification logs** to verify the system works

Update `apps/notifications/services.py`:

```python
def get_firebase_app():
    """Initialize and return Firebase app instance"""
    global _firebase_app
    if _firebase_app is None:
        try:
            # Temporarily disable Firebase for testing
            logger.warning("Firebase not configured - notifications will be logged only")
            return None  # Return None to skip Firebase
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {str(e)}")
            return None
    return _firebase_app
```

Then update `send_notification` to log only:

```python
# In send_notification method, add at the beginning:
if not get_firebase_app():
    # Log notification attempt without sending
    NotificationLog.objects.create(
        user=user,
        notification_type=notification_type,
        category=category,
        title=title,
        body=body,
        data=data or {},
        status='pending',
        error_message="Firebase not configured - logged only"
    )
    return True  # Return True to indicate "success" (logged)
```

This way you can test the entire notification flow and verify logs without Firebase credentials!


