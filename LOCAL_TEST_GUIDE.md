# Local Firebase Testing Guide

## ✅ Firebase Status

Firebase is now initialized successfully! Project: `mgask-2025`

---

## Step 1: Start Django Server

```bash
python manage.py runserver
```

Keep it running in one terminal.

---

## Step 2: Get JWT Token

You need a JWT token for testing. Login as a user (customer, tailor, or rider):

```bash
# Example: Login as tailor
curl --location 'http://localhost:8000/api/accounts/login/' \
--header 'Content-Type: application/json' \
--data '{
    "username": "your_username",
    "password": "your_password"
}'
```

Copy the `access_token` from the response.

---

## Step 3: Register FCM Token

**Option A: Use Real FCM Token from Flutter App**

Get FCM token from your Flutter app and register it:

```bash
curl --location 'http://localhost:8000/api/notifications/fcm-token/register/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer YOUR_JWT_TOKEN' \
--data '{
    "token": "REAL_FCM_TOKEN_FROM_FLUTTER_APP",
    "device_type": "android",
    "device_id": "device_123"
}'
```

**Option B: Use Test Token (for API testing only)**

```bash
curl --location 'http://localhost:8000/api/notifications/fcm-token/register/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer YOUR_JWT_TOKEN' \
--data '{
    "token": "test_token_for_api_testing",
    "device_type": "android",
    "device_id": "test_device_1"
}'
```

**Expected Response:**
```json
{
    "success": true,
    "message": "FCM token registered successfully",
    "data": {
        "id": 1,
        "token": "...",
        "device_type": "android",
        "is_active": true
    }
}
```

---

## Step 4: Test Notification

### For Tailors (Test Endpoint)

```bash
curl -X POST 'http://localhost:8000/api/notifications/test/' \
--header 'Authorization: Bearer TAILOR_JWT_TOKEN'
```

**Expected Response:**
```json
{
    "success": true,
    "message": "Test notification sent successfully! Check your device.",
    "data": {
        "user": "tailor_username",
        "fcm_tokens_count": 1
    }
}
```

### Check Notification Logs

```bash
curl 'http://localhost:8000/api/notifications/logs/' \
--header 'Authorization: Bearer YOUR_JWT_TOKEN'
```

**Expected:** Status should be `"sent"` (not `"pending"`)

---

## Step 5: Test Real Order Flow

### Create Order (Customer)

```bash
curl --location 'http://localhost:8000/api/orders/create/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer CUSTOMER_TOKEN' \
--data '{
    "tailor": TAILOR_USER_ID,
    "order_type": "fabric_with_stitching",
    "payment_method": "credit_card",
    "delivery_address": ADDRESS_ID,
    "items": [{"fabric": FABRIC_ID, "quantity": 1}]
}'
```

**Expected:** Tailor should receive notification: "New order #ORD-XXXXX received"

### Confirm Order (Tailor)

```bash
curl --location --request PATCH 'http://localhost:8000/api/orders/ORDER_ID/status/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer TAILOR_TOKEN' \
--data '{"status": "confirmed"}'
```

**Expected:** Customer should receive notification: "Tailor has accepted your order"

---

## Troubleshooting

### Firebase Not Initialized

If you see `"Firebase not initialized"`:

```bash
# Re-authenticate
gcloud auth application-default login

# Set project
gcloud config set project mgask-2025

# Test again
python3 test_firebase_init.py
```

### Notification Status is "pending"

This means Firebase initialized but notification wasn't sent. Check:

1. **FCM token is registered:**
   ```bash
   GET /api/notifications/logs/
   ```

2. **Check Django logs** for errors:
   ```bash
   # In Django server terminal, look for errors
   ```

3. **Test Firebase directly:**
   ```bash
   python3 test_firebase_init.py
   ```

### "No active FCM tokens found"

**Solution:**
- Make sure you registered FCM token first (Step 3)
- Check token is active: `GET /api/notifications/logs/`

---

## Quick Test Checklist

- [ ] Firebase initialized: `python3 test_firebase_init.py` shows ✅
- [ ] Django server running: `python manage.py runserver`
- [ ] JWT token obtained from login
- [ ] FCM token registered: `POST /api/notifications/fcm-token/register/`
- [ ] Test notification sent: `POST /api/notifications/test/`
- [ ] Notification log shows `"status": "sent"`

---

## Next Steps

Once local testing works:

1. ✅ Test with real FCM token from Flutter app
2. ✅ Test complete order flow
3. ✅ Deploy to server
4. ✅ Set `FIREBASE_SERVER_KEY` on server (if Admin SDK doesn't work there)

---

## Summary

✅ **Firebase is initialized locally!**  
✅ **Ready to test notifications!**  
✅ **Use the curl commands above to test**

Start with Step 1-4 to test basic notification sending! 🚀

