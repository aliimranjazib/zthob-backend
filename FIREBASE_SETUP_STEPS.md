# Firebase Push Notifications - Step-by-Step Setup

## 🎯 Quick Start (5 Steps)

### Step 1: Install Google Cloud SDK

```bash
# macOS
brew install google-cloud-sdk

# Or download from: https://cloud.google.com/sdk/docs/install
```

### Step 2: Authenticate

```bash
# Login with your Google account (same as Firebase)
gcloud auth application-default login

# Set your Firebase project
gcloud config set project mgask-2025

# Verify
gcloud config get-value project
# Should output: mgask-2025
```

### Step 3: Install Firebase Admin SDK

```bash
# Using uv (your package manager)
uv pip install firebase-admin

# Or using pip
pip install firebase-admin
```

### Step 4: Run Migrations

```bash
python manage.py migrate notifications
```

### Step 5: Test Firebase Connection

```bash
python manage.py shell
```

Then in Python shell:
```python
from apps.notifications.services import get_firebase_app

app = get_firebase_app()
if app:
    print("✅ Firebase initialized successfully!")
else:
    print("❌ Firebase not initialized - check authentication")
```

**Expected:** `✅ Firebase initialized successfully!`

---

## ✅ That's It!

Your Django backend is now ready to send push notifications!

---

## 🔗 Next: Connect Flutter App

### In Your Flutter App:

1. **Get FCM Token:**
   ```dart
   String? token = await FirebaseMessaging.instance.getToken();
   print("FCM Token: $token");
   ```

2. **Send Token to Django:**
   ```dart
   // When user logs in or app starts
   await http.post(
     Uri.parse('YOUR_BASE_URL/api/notifications/fcm-token/register/'),
     headers: {
       'Content-Type': 'application/json',
       'Authorization': 'Bearer $userToken',
     },
     body: jsonEncode({
       'token': token,
       'device_type': Platform.isAndroid ? 'android' : 'ios',
     }),
   );
   ```

3. **Test:** Create an order → Tailor should receive notification!

---

## 📋 Verification Checklist

- [ ] `gcloud auth application-default login` completed
- [ ] `gcloud config set project mgask-2025` completed
- [ ] `firebase-admin` installed
- [ ] Migrations run: `python manage.py migrate notifications`
- [ ] Firebase test passed: `✅ Firebase initialized successfully!`
- [ ] FCM token registered from Flutter app
- [ ] Test notification sent and received

---

## 🐛 Troubleshooting

### "Firebase not initialized"

```bash
# Re-authenticate
gcloud auth application-default login
gcloud config set project mgask-2025

# Test again
python manage.py shell
```

### "Permission denied"

- Use the same Google account as Firebase
- Check Firebase Cloud Messaging API is enabled
- Verify project ID is `mgask-2025`

### Notifications not received

1. Check FCM token is registered: `GET /api/notifications/logs/`
2. Verify Firebase project matches between Flutter and Django
3. Check device has internet and notification permissions

---

## 📚 Full Documentation

- **Complete Guide:** `FIREBASE_SETUP_COMPLETE_GUIDE.md`
- **Quick Fix:** `FIREBASE_QUICK_FIX.md`
- **Alternatives:** `FIREBASE_SETUP_ALTERNATIVES.md`
- **Checklist:** `SETUP_CHECKLIST.md`

---

## 🎉 You're Done!

Your Django backend can now send push notifications to your Flutter app!

