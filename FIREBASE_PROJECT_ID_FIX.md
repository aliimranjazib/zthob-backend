# Firebase Project ID Error - Fixed! ✅

## Problem

Error: `"Project ID is required to access Cloud Messaging service. Either set the projectId option, or use service account credentials. Alternatively, set the GOOGLE_CLOUD_PROJECT environment variable."`

## Solution Applied

I've updated `apps/notifications/services.py` to explicitly pass the project ID when initializing Firebase.

### What Changed

The code now:
1. ✅ Gets project ID from `settings.py` (`FIREBASE_PROJECT_ID = 'mgask-2025'`)
2. ✅ Or from environment variable (`GOOGLE_CLOUD_PROJECT` or `FIREBASE_PROJECT_ID`)
3. ✅ Explicitly passes it to Firebase: `initialize_app({'projectId': project_id})`

### Your Settings

Your `settings.py` already has:
```python
FIREBASE_PROJECT_ID = os.getenv('FIREBASE_PROJECT_ID', 'mgask-2025')
```

This is correct! ✅

---

## Test Again

### Step 1: Restart Django Server

```bash
# Stop your server (Ctrl+C) and restart
python manage.py runserver
```

### Step 2: Test Firebase Initialization

```bash
python manage.py shell
```

```python
from apps.notifications.services import get_firebase_app

app = get_firebase_app()
if app:
    print("✅ Firebase initialized successfully!")
    print(f"Project: {app.project_id}")
else:
    print("❌ Firebase not initialized")
```

**Expected output:**
```
✅ Firebase initialized successfully!
Project: mgask-2025
```

### Step 3: Test Sending Notification

```python
from apps.notifications.services import NotificationService
from apps.accounts.models import CustomUser

user = CustomUser.objects.first()

# This should work now (even without FCM token, it will log)
NotificationService.send_notification(
    user=user,
    title="Test",
    body="Test notification",
    notification_type="SYSTEM",
    category="test"
)

print("✅ Notification service called successfully!")
```

---

## Alternative: Set Environment Variable

If you prefer using environment variable instead:

```bash
# Set environment variable
export GOOGLE_CLOUD_PROJECT=mgask-2025

# Or
export FIREBASE_PROJECT_ID=mgask-2025

# Then restart Django server
python manage.py runserver
```

---

## Verify Settings

Make sure your `zthob/settings.py` has:

```python
# Firebase Configuration
FIREBASE_PROJECT_ID = os.getenv('FIREBASE_PROJECT_ID', 'mgask-2025')
```

This should already be there! ✅

---

## What to Check

1. ✅ `FIREBASE_PROJECT_ID` is set in `settings.py` (should be `'mgask-2025'`)
2. ✅ Django server restarted after code change
3. ✅ `gcloud auth application-default login` completed
4. ✅ `gcloud config set project mgask-2025` completed

---

## Expected Behavior

After the fix:
- ✅ Firebase initializes with project ID: `mgask-2025`
- ✅ No more "Project ID is required" error
- ✅ Notifications can be sent successfully

---

## Still Having Issues?

If you still see errors:

1. **Check Django logs:**
   ```bash
   tail -f logs/django.log | grep -i firebase
   ```

2. **Verify project ID:**
   ```python
   python manage.py shell
   from django.conf import settings
   print(settings.FIREBASE_PROJECT_ID)  # Should print: mgask-2025
   ```

3. **Test Firebase directly:**
   ```python
   import firebase_admin
   from firebase_admin import credentials
   
   app = firebase_admin.initialize_app({'projectId': 'mgask-2025'})
   print(f"✅ Firebase initialized: {app.project_id}")
   ```

---

## Summary

✅ **Fixed:** Code now explicitly passes project ID to Firebase  
✅ **Settings:** Already configured correctly (`FIREBASE_PROJECT_ID = 'mgask-2025'`)  
✅ **Next:** Restart Django server and test again!

The error should be resolved now! 🎉

