# Firebase Push Notifications - Complete Setup Guide for Django Backend

## Prerequisites

- ✅ Flutter app already connected to Firebase
- ✅ Django project with notifications app installed
- ✅ Google Cloud SDK installed (for authentication)

---

## Step 1: Get Firebase Project Information

Since your Flutter app is already connected to Firebase, you have a Firebase project. We need to use the same project.

### 1.1 Find Your Firebase Project ID

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project (or create one if needed)
3. Click on **Project Settings** (gear icon)
4. Note your **Project ID** (e.g., `mgask-2025`)

### 1.2 Enable Cloud Messaging API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your Firebase project (`mgask-2025`)
3. Go to **APIs & Services** > **Library**
4. Search for **"Firebase Cloud Messaging API"**
5. Click **Enable** (if not already enabled)

---

## Step 2: Set Up Authentication (Recommended Method)

We'll use **Application Default Credentials (ADC)** - this is the recommended method and works even when service account key creation is restricted.

### 2.1 Install Google Cloud SDK

**macOS:**
```bash
brew install google-cloud-sdk
```

**Linux:**
```bash
# Download and install from:
# https://cloud.google.com/sdk/docs/install
```

**Windows:**
Download installer from: https://cloud.google.com/sdk/docs/install

### 2.2 Authenticate with Google Cloud

```bash
# Login with your Google account (use the same account as Firebase)
gcloud auth application-default login

# Set your Firebase project
gcloud config set project mgask-2025

# Verify it's set correctly
gcloud config get-value project
```

**Expected output:** `mgask-2025`

### 2.3 Verify Authentication

```bash
# Test authentication
gcloud auth list
```

You should see your account listed.

---

## Step 3: Configure Django Settings

### 3.1 Update `zthob/settings.py`

Add Firebase configuration (but **don't** set `FIREBASE_CREDENTIALS_PATH` - we're using ADC):

```python
# Firebase Configuration
# Using Application Default Credentials (ADC)
# No FIREBASE_CREDENTIALS_PATH needed - ADC will be used automatically

# Optional: Set Firebase project ID (for reference)
FIREBASE_PROJECT_ID = 'mgask-2025'

# Optional: For debugging
FIREBASE_DEBUG = DEBUG  # Use DEBUG setting from Django
```

**Important:** Do NOT add `FIREBASE_CREDENTIALS_PATH` - the code will automatically use Application Default Credentials.

### 3.2 Verify Settings

Your `settings.py` should have:
- ✅ `apps.notifications` in `INSTALLED_APPS`
- ✅ No `FIREBASE_CREDENTIALS_PATH` set (or set to `None`)

---

## Step 4: Install Dependencies

### 4.1 Install Firebase Admin SDK

```bash
# Using uv (your package manager)
uv pip install firebase-admin

# Or using pip
pip install firebase-admin
```

### 4.2 Verify Installation

```bash
python -c "import firebase_admin; print('Firebase Admin SDK installed successfully')"
```

---

## Step 5: Run Migrations

```bash
# Create migration tables for notifications
python manage.py migrate notifications
```

---

## Step 6: Test Firebase Connection

### 6.1 Test in Django Shell

```bash
python manage.py shell
```

```python
# Test Firebase initialization
from apps.notifications.services import get_firebase_app

try:
    app = get_firebase_app()
    if app:
        print("✅ Firebase initialized successfully!")
        print(f"Project: {app.project_id}")
    else:
        print("⚠️ Firebase not initialized - using ADC")
except Exception as e:
    print(f"❌ Error: {e}")
```

**Expected output:** `✅ Firebase initialized successfully!`

### 6.2 Test Notification Sending

```python
# In Django shell
from apps.notifications.services import NotificationService
from apps.accounts.models import CustomUser

# Get a test user
user = CustomUser.objects.first()

# Register a test FCM token first (you'll get this from Flutter app)
# Then test sending notification
NotificationService.send_notification(
    user=user,
    title="Test Notification",
    body="This is a test from Django",
    notification_type="SYSTEM",
    category="test",
    data={"test": "true"}
)

print("✅ Notification sent! Check notification logs.")
```

---

## Step 7: Get FCM Token from Flutter App

Your Flutter app needs to send the FCM token to your Django backend.

### 7.1 In Flutter App

Make sure you have Firebase Cloud Messaging set up and can get the FCM token:

```dart
// Example Flutter code (you may already have this)
FirebaseMessaging messaging = FirebaseMessaging.instance;
String? token = await messaging.getToken();
print("FCM Token: $token");
```

### 7.2 Send Token to Django Backend

When user logs in or app starts, send the token to your Django API:

```dart
// Example: Send FCM token to Django
Future<void> registerFCMToken(String token) async {
  final response = await http.post(
    Uri.parse('YOUR_BASE_URL/api/notifications/fcm-token/register/'),
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer $userToken',
    },
    body: jsonEncode({
      'token': token,
      'device_type': Platform.isAndroid ? 'android' : 'ios',
      'device_id': await _getDeviceId(),
    }),
  );
  
  if (response.statusCode == 201) {
    print('FCM token registered successfully');
  }
}
```

---

## Step 8: Test Complete Flow

### 8.1 Register FCM Token

```bash
curl --location 'YOUR_BASE_URL/api/notifications/fcm-token/register/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer YOUR_JWT_TOKEN' \
--data '{
    "token": "FCM_TOKEN_FROM_FLUTTER_APP",
    "device_type": "android",
    "device_id": "device_123"
}'
```

### 8.2 Create an Order (to trigger notification)

```bash
curl --location 'YOUR_BASE_URL/api/orders/create/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer CUSTOMER_TOKEN' \
--data '{
    "tailor": TAILOR_ID,
    "order_type": "fabric_with_stitching",
    "payment_method": "credit_card",
    "delivery_address": ADDRESS_ID,
    "items": [{"fabric": FABRIC_ID, "quantity": 1}]
}'
```

**Expected:** Tailor should receive push notification on their device!

### 8.3 Check Notification Logs

```bash
curl --location 'YOUR_BASE_URL/api/notifications/logs/' \
--header 'Authorization: Bearer YOUR_TOKEN'
```

---

## Step 9: Verify Everything Works

### Checklist:

- [ ] Google Cloud SDK installed
- [ ] Authenticated with `gcloud auth application-default login`
- [ ] Project set: `gcloud config set project mgask-2025`
- [ ] Firebase Admin SDK installed
- [ ] Migrations run: `python manage.py migrate notifications`
- [ ] Firebase initialized successfully (tested in shell)
- [ ] FCM token registered from Flutter app
- [ ] Test notification sent and received

---

## Step 10: Production Deployment

### For Production (Google Cloud Run / App Engine / Compute Engine)

1. **Attach Service Account:**
   - When deploying, attach the Firebase service account to your instance
   - ADC will automatically use the attached service account
   - No credentials file needed!

2. **Environment Variables (Optional):**
   ```bash
   export GOOGLE_CLOUD_PROJECT=mgask-2025
   ```

3. **Verify in Production:**
   - Check Django logs for: `Firebase initialized using Application Default Credentials`
   - Test sending a notification
   - Check notification logs

---

## Troubleshooting

### Issue: "Firebase not initialized"

**Solution:**
```bash
# Re-authenticate
gcloud auth application-default login

# Verify project
gcloud config set project mgask-2025

# Test again
python manage.py shell
# Then run: from apps.notifications.services import get_firebase_app
```

### Issue: "Permission denied"

**Solution:**
- Make sure you're using the same Google account as Firebase
- Check that Firebase Cloud Messaging API is enabled
- Verify project ID is correct

### Issue: "No active FCM tokens found"

**Solution:**
- Make sure FCM token is registered: `POST /api/notifications/fcm-token/register/`
- Check token is active in database
- Verify token from Flutter app is valid

### Issue: Notifications not received on device

**Solution:**
1. Check notification logs: `GET /api/notifications/logs/`
2. Verify FCM token is correct
3. Check device has internet connection
4. Verify Firebase project matches between Flutter and Django
5. Check device notification permissions

---

## Quick Reference

### Important Commands

```bash
# Authenticate
gcloud auth application-default login

# Set project
gcloud config set project mgask-2025

# Install dependencies
uv pip install firebase-admin

# Run migrations
python manage.py migrate notifications

# Test Firebase
python manage.py shell
# Then: from apps.notifications.services import get_firebase_app
```

### Important URLs

- Firebase Console: https://console.firebase.google.com/
- Google Cloud Console: https://console.cloud.google.com/
- Your API Base: `YOUR_BASE_URL/api/notifications/`

### API Endpoints

- Register Token: `POST /api/notifications/fcm-token/register/`
- Update Token: `PUT /api/notifications/fcm-token/update/`
- Unregister Token: `POST /api/notifications/fcm-token/unregister/`
- View Logs: `GET /api/notifications/logs/`

---

## Next Steps

1. ✅ Complete setup (Steps 1-6)
2. ✅ Test Firebase connection (Step 6)
3. ✅ Integrate with Flutter app (Step 7)
4. ✅ Test complete flow (Step 8)
5. ✅ Deploy to production (Step 10)

---

## Summary

**What we did:**
1. Used Application Default Credentials (no JSON file needed)
2. Authenticated with `gcloud auth application-default login`
3. Set project to `mgask-2025`
4. Configured Django to use ADC automatically
5. Tested Firebase initialization
6. Ready to receive FCM tokens from Flutter app

**Result:** Your Django backend can now send push notifications to your Flutter app! 🎉

---

## Need Help?

- Check `FIREBASE_QUICK_FIX.md` for quick solutions
- Check `FIREBASE_SETUP_ALTERNATIVES.md` for alternative methods
- Check Django logs: `tail -f logs/django.log`
- Check notification logs: `GET /api/notifications/logs/`

