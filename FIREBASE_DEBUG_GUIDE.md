# Firebase Not Initializing - Debug Guide

## Problem

Firebase is not initializing. Notifications are being logged but not sent. Error shows: "Firebase not initialized - logged only"

## Quick Diagnostic

Run this command to check Firebase configuration:

```bash
python manage.py test_firebase
```

This will show you:
- ✅ Settings configuration
- ✅ Environment variables
- ✅ Credentials file status
- ✅ gcloud authentication status
- ✅ Firebase initialization test

## Step-by-Step Fix

### Step 1: Check Django Logs

The improved error logging will now show the actual error. Check your Django logs:

```bash
# Check logs for Firebase errors
tail -f logs/django.log | grep -i firebase

# Or if running in terminal, check the console output
```

Look for lines starting with `ERROR` that show the actual Firebase initialization error.

### Step 2: Verify gcloud Authentication

```bash
# Check if authenticated
gcloud auth list

# Should show your account with ACTIVE status
# If not, run:
gcloud auth application-default login
```

### Step 3: Verify Project Configuration

```bash
# Check current project
gcloud config get-value project

# Should show: mgask-2025
# If not, set it:
gcloud config set project mgask-2025

# Verify
gcloud config get-value project
```

### Step 4: Test Firebase Directly

```bash
python manage.py shell
```

```python
# Test Firebase initialization with detailed error
from apps.notifications.services import get_firebase_app
import traceback

try:
    app = get_firebase_app()
    if app:
        print(f"✅ Firebase initialized! Project: {app.project_id}")
    else:
        print("❌ Firebase returned None")
except Exception as e:
    print(f"❌ Error: {e}")
    traceback.print_exc()
```

### Step 5: Check Settings

```python
python manage.py shell
```

```python
from django.conf import settings
import os

print(f"FIREBASE_PROJECT_ID: {getattr(settings, 'FIREBASE_PROJECT_ID', 'NOT SET')}")
print(f"GOOGLE_CLOUD_PROJECT env: {os.environ.get('GOOGLE_CLOUD_PROJECT', 'NOT SET')}")
print(f"FIREBASE_PROJECT_ID env: {os.environ.get('FIREBASE_PROJECT_ID', 'NOT SET')}")
```

**Expected:**
```
FIREBASE_PROJECT_ID: mgask-2025
GOOGLE_CLOUD_PROJECT env: NOT SET (or mgask-2025)
FIREBASE_PROJECT_ID env: NOT SET (or mgask-2025)
```

## Common Issues & Solutions

### Issue 1: "Could not automatically determine credentials"

**Solution:**
```bash
# Re-authenticate
gcloud auth application-default login

# Set project
gcloud config set project mgask-2025

# Restart Django server
```

### Issue 2: "Permission denied" or "Access denied"

**Solution:**
- Make sure you're using the same Google account as Firebase
- Check Firebase Cloud Messaging API is enabled:
  - Go to: https://console.cloud.google.com/apis/library/fcm.googleapis.com
  - Click "Enable"

### Issue 3: "Project ID mismatch"

**Solution:**
```bash
# Make sure gcloud project matches settings
gcloud config set project mgask-2025

# Verify
gcloud config get-value project
# Should output: mgask-2025
```

### Issue 4: Application Default Credentials not found

**Solution:**
```bash
# Create ADC credentials
gcloud auth application-default login

# This will open browser for authentication
# After successful login, credentials are stored locally
```

## Test After Fix

After fixing the issue:

1. **Restart Django server:**
   ```bash
   # Stop server (Ctrl+C) and restart
   python manage.py runserver
   ```

2. **Run diagnostic:**
   ```bash
   python manage.py test_firebase
   ```

3. **Test notification:**
   ```bash
   # Use your test endpoint
   curl -X POST 'YOUR_BASE_URL/api/notifications/test/' \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

4. **Check notification log:**
   ```bash
   curl 'YOUR_BASE_URL/api/notifications/logs/' \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

   **Expected:** Status should be `"sent"` instead of `"pending"`

## Alternative: Use Firebase REST API

If Application Default Credentials continue to fail, you can use Firebase REST API instead:

1. **Get Firebase Server Key:**
   - Go to Firebase Console
   - Project Settings > Cloud Messaging
   - Copy "Server key" (Legacy)

2. **Add to settings.py:**
   ```python
   FIREBASE_SERVER_KEY = os.getenv('FIREBASE_SERVER_KEY', 'your-server-key')
   ```

3. **See:** `FIREBASE_SETUP_ALTERNATIVES.md` for REST API implementation

## Next Steps

1. ✅ Run `python manage.py test_firebase` to diagnose
2. ✅ Check Django logs for detailed error messages
3. ✅ Fix authentication/project configuration
4. ✅ Test notification again
5. ✅ Verify notification log shows `"status": "sent"`

---

## Quick Commands Reference

```bash
# Diagnostic
python manage.py test_firebase

# Check authentication
gcloud auth list
gcloud auth application-default login

# Check project
gcloud config get-value project
gcloud config set project mgask-2025

# Check logs
tail -f logs/django.log | grep -i firebase

# Test in shell
python manage.py shell
# Then: from apps.notifications.services import get_firebase_app
```

