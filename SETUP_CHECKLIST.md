# Firebase Push Notifications - Setup Checklist

Use this checklist to ensure everything is set up correctly.

## ✅ Pre-Setup Verification

- [ ] Flutter app is connected to Firebase
- [ ] Firebase project exists (mgask-2025)
- [ ] You have access to Firebase Console
- [ ] Django project is running

---

## ✅ Step 1: Google Cloud SDK Setup

- [ ] Google Cloud SDK installed
  ```bash
  gcloud --version
  ```

- [ ] Authenticated with Google account
  ```bash
  gcloud auth application-default login
  ```

- [ ] Project set to mgask-2025
  ```bash
  gcloud config set project mgask-2025
  gcloud config get-value project  # Should show: mgask-2025
  ```

---

## ✅ Step 2: Firebase API Setup

- [ ] Firebase Cloud Messaging API enabled
  - Go to: https://console.cloud.google.com/apis/library/fcm.googleapis.com
  - Click "Enable"

---

## ✅ Step 3: Django Configuration

- [ ] Firebase Admin SDK installed
  ```bash
  uv pip install firebase-admin
  # Or: pip install firebase-admin
  ```

- [ ] Settings.py configured
  - Check: `FIREBASE_PROJECT_ID = 'mgask-2025'` exists in settings.py
  - Check: `apps.notifications` in INSTALLED_APPS
  - Check: NO `FIREBASE_CREDENTIALS_PATH` set (or set to None)

- [ ] Migrations run
  ```bash
  python manage.py migrate notifications
  ```

---

## ✅ Step 4: Firebase Connection Test

- [ ] Test Firebase initialization
  ```bash
  python manage.py shell
  ```
  ```python
  from apps.notifications.services import get_firebase_app
  app = get_firebase_app()
  print("✅ Firebase initialized!" if app else "❌ Firebase not initialized")
  ```

- [ ] Check logs for success message
  - Should see: "Firebase initialized using Application Default Credentials"

---

## ✅ Step 5: Flutter App Integration

- [ ] FCM token can be retrieved in Flutter app
  ```dart
  String? token = await FirebaseMessaging.instance.getToken();
  ```

- [ ] API endpoint to register token works
  ```bash
  POST /api/notifications/fcm-token/register/
  ```

- [ ] Token registered successfully
  - Check response: `{"success": true}`

---

## ✅ Step 6: End-to-End Test

- [ ] Register FCM token from Flutter app
- [ ] Create an order (triggers notification to tailor)
- [ ] Tailor receives push notification on device
- [ ] Check notification logs
  ```bash
  GET /api/notifications/logs/
  ```

---

## ✅ Step 7: Test All Notification Types

- [ ] Order status change notifications work
- [ ] Payment status change notifications work
- [ ] Rider assignment notifications work
- [ ] All relevant users receive notifications

---

## 🎉 Setup Complete!

If all items are checked, your Firebase push notifications are fully configured!

---

## Troubleshooting

### If Firebase not initialized:
```bash
# Re-authenticate
gcloud auth application-default login
gcloud config set project mgask-2025

# Test again
python manage.py shell
```

### If notifications not received:
1. Check FCM token is registered
2. Check notification logs: `GET /api/notifications/logs/`
3. Verify Firebase project matches between Flutter and Django
4. Check device has internet and notification permissions

### If "Permission denied":
- Verify same Google account used for Firebase and gcloud
- Check Firebase Cloud Messaging API is enabled
- Verify project ID is correct

---

## Quick Commands Reference

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

