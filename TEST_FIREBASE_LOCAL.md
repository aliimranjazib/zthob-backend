# Test Firebase Notifications Locally

## Step-by-Step Local Testing

### Step 1: Verify gcloud Setup

```bash
# Check if gcloud is installed
gcloud --version

# Check authentication
gcloud auth list

# Check project
gcloud config get-value project
```

**Expected:** Should show `mgask-2025`

If not set:
```bash
gcloud config set project mgask-2025
```

### Step 2: Authenticate (if not done)

```bash
gcloud auth application-default login
```

This will open a browser for authentication.

### Step 3: Test Firebase Initialization

```bash
python manage.py shell
```

Then in Python shell:
```python
from apps.notifications.services import get_firebase_app

app = get_firebase_app()
if app:
    print(f"✅ Firebase initialized! Project: {app.project_id}")
else:
    print("❌ Firebase not initialized - check logs")
```

### Step 4: Register a Test FCM Token

You'll need a real FCM token from your Flutter app. For testing, you can use a dummy token first to test the API:

```bash
curl --location 'http://localhost:8000/api/notifications/fcm-token/register/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer YOUR_JWT_TOKEN' \
--data '{
    "token": "test_token_12345",
    "device_type": "android",
    "device_id": "test_device_1"
}'
```

### Step 5: Test Sending Notification

```bash
curl -X POST 'http://localhost:8000/api/notifications/test/' \
--header 'Authorization: Bearer YOUR_JWT_TOKEN'
```

### Step 6: Check Notification Logs

```bash
curl 'http://localhost:8000/api/notifications/logs/' \
--header 'Authorization: Bearer YOUR_JWT_TOKEN'
```

---

## Quick Test Script

Save this as `test_firebase_local.sh`:

```bash
#!/bin/bash

BASE_URL="http://localhost:8000"
TOKEN="YOUR_JWT_TOKEN_HERE"

echo "=== Testing Firebase Notifications Locally ==="

echo "1. Testing Firebase initialization..."
python manage.py shell << EOF
from apps.notifications.services import get_firebase_app
app = get_firebase_app()
if app:
    print("✅ Firebase initialized!")
else:
    print("❌ Firebase not initialized")
EOF

echo ""
echo "2. Registering test FCM token..."
curl -s -X POST "$BASE_URL/api/notifications/fcm-token/register/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"token": "test_token_123", "device_type": "android"}' | jq

echo ""
echo "3. Sending test notification..."
curl -s -X POST "$BASE_URL/api/notifications/test/" \
  -H "Authorization: Bearer $TOKEN" | jq

echo ""
echo "4. Checking notification logs..."
curl -s "$BASE_URL/api/notifications/logs/" \
  -H "Authorization: Bearer $TOKEN" | jq

echo ""
echo "=== Test Complete ==="
```

Make it executable:
```bash
chmod +x test_firebase_local.sh
```

Run:
```bash
./test_firebase_local.sh
```

