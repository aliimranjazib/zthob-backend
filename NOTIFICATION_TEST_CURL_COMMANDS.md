# Push Notifications - Complete Test CURL Commands

This document contains all CURL commands to test Phase 1 push notifications implementation.

## Prerequisites

1. Replace `YOUR_BASE_URL` with your server URL (e.g., `http://localhost:8000` or `http://69.62.126.95`)
2. Replace `CUSTOMER_TOKEN`, `TAILOR_TOKEN`, `RIDER_TOKEN` with actual JWT access tokens
3. Replace `FCM_TOKEN_CUSTOMER`, `FCM_TOKEN_TAILOR`, `FCM_TOKEN_RIDER` with actual FCM device tokens
4. Replace `ORDER_ID`, `FABRIC_ID`, `ADDRESS_ID`, etc. with actual IDs from your database

---

## 1. FCM Token Management

### 1.1 Register FCM Token (Customer)

```bash
curl --location 'YOUR_BASE_URL/api/notifications/fcm-token/register/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer CUSTOMER_TOKEN' \
--data '{
    "token": "FCM_TOKEN_CUSTOMER",
    "device_type": "android",
    "device_id": "customer_device_123"
}'
```

### 1.2 Register FCM Token (Tailor)

```bash
curl --location 'YOUR_BASE_URL/api/notifications/fcm-token/register/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer TAILOR_TOKEN' \
--data '{
    "token": "FCM_TOKEN_TAILOR",
    "device_type": "android",
    "device_id": "tailor_device_456"
}'
```

### 1.3 Register FCM Token (Rider)

```bash
curl --location 'YOUR_BASE_URL/api/notifications/fcm-token/register/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer RIDER_TOKEN' \
--data '{
    "token": "FCM_TOKEN_RIDER",
    "device_type": "android",
    "device_id": "rider_device_789"
}'
```

### 1.4 Update FCM Token

```bash
curl --location --request PUT 'YOUR_BASE_URL/api/notifications/fcm-token/update/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer CUSTOMER_TOKEN' \
--data '{
    "token": "NEW_FCM_TOKEN",
    "device_type": "ios"
}'
```

### 1.5 Unregister FCM Token

```bash
curl --location 'YOUR_BASE_URL/api/notifications/fcm-token/unregister/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer CUSTOMER_TOKEN' \
--data '{
    "token": "FCM_TOKEN_CUSTOMER"
}'
```

### 1.6 View Notification Logs

```bash
curl --location 'YOUR_BASE_URL/api/notifications/logs/' \
--header 'Authorization: Bearer CUSTOMER_TOKEN'
```

---

## 2. Order Status Notifications

### 2.1 Create Order (Triggers "pending" notification to tailor)

```bash
curl --location 'YOUR_BASE_URL/api/orders/create/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer CUSTOMER_TOKEN' \
--data '{
    "tailor": TAILOR_USER_ID,
    "order_type": "fabric_with_stitching",
    "payment_method": "credit_card",
    "delivery_address": ADDRESS_ID,
    "items": [
        {
            "fabric": FABRIC_ID,
            "quantity": 2,
            "measurements": {},
            "custom_instructions": "Please make it comfortable"
        }
    ],
    "special_instructions": "Handle with care",
    "distance_km": "5.5"
}'
```

**Expected Notifications:**
- ✅ Tailor receives: "New order #ORD-XXXXX received from [Customer Name]"

### 2.2 Update Order Status: pending → confirmed (Tailor)

```bash
curl --location --request PATCH 'YOUR_BASE_URL/api/orders/ORDER_ID/status/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer TAILOR_TOKEN' \
--data '{
    "status": "confirmed"
}'
```

**Expected Notifications:**
- ✅ Customer receives: "Tailor has accepted your order #ORD-XXXXX"
- ✅ Tailor receives: "You have confirmed order #ORD-XXXXX"

### 2.3 Update Payment Status: pending → paid (Customer/Admin)

```bash
curl --location --request PATCH 'YOUR_BASE_URL/api/orders/ORDER_ID/payment-status/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer CUSTOMER_TOKEN' \
--data '{
    "payment_status": "paid"
}'
```

**Expected Notifications:**
- ✅ Customer receives: "Payment of $X.XX received for order #ORD-XXXXX"
- ✅ Tailor receives: "Payment received for order #ORD-XXXXX - $X.XX"

### 2.4 Rider Accepts Order (Triggers rider assignment notifications)

```bash
curl --location 'YOUR_BASE_URL/api/riders/orders/ORDER_ID/accept/' \
--header 'Authorization: Bearer RIDER_TOKEN' \
--data ''
```

**Expected Notifications:**
- ✅ Customer receives: "Rider [Name] has been assigned to deliver your order #ORD-XXXXX"
- ✅ Tailor receives: "Rider [Name] will pick up order #ORD-XXXXX"
- ✅ Rider receives: "You have been assigned to order #ORD-XXXXX"

**Note:** For `fabric_with_stitching` orders, status automatically changes to `measuring`:
- ✅ Customer receives: "Rider is on the way to take your measurements for order #ORD-XXXXX"
- ✅ Rider receives: "Please take measurements for order #ORD-XXXXX"

### 2.5 Update Order Status: measuring → cutting (Tailor)

```bash
curl --location --request PATCH 'YOUR_BASE_URL/api/orders/ORDER_ID/status/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer TAILOR_TOKEN' \
--data '{
    "status": "cutting"
}'
```

**Expected Notifications:**
- ✅ Customer receives: "Fabric cutting has started for your order #ORD-XXXXX"
- ✅ Tailor receives: "Order #ORD-XXXXX is ready for cutting"

### 2.6 Update Order Status: cutting → stitching (Tailor)

```bash
curl --location --request PATCH 'YOUR_BASE_URL/api/orders/ORDER_ID/status/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer TAILOR_TOKEN' \
--data '{
    "status": "stitching"
}'
```

**Expected Notifications:**
- ✅ Customer receives: "Your garment is being stitched for order #ORD-XXXXX"
- ✅ Tailor receives: "Order #ORD-XXXXX is ready for stitching"

### 2.7 Update Order Status: stitching → ready_for_delivery (Tailor)

```bash
curl --location --request PATCH 'YOUR_BASE_URL/api/orders/ORDER_ID/status/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer TAILOR_TOKEN' \
--data '{
    "status": "ready_for_delivery"
}'
```

**Expected Notifications:**
- ✅ Customer receives: "Your order #ORD-XXXXX is ready for delivery"
- ✅ Tailor receives: "Order #ORD-XXXXX is ready for pickup"
- ✅ Rider receives: "Order #ORD-XXXXX is ready for pickup from tailor"

### 2.8 Rider Updates Status: ready_for_delivery → delivered

```bash
curl --location --request PATCH 'YOUR_BASE_URL/api/riders/orders/ORDER_ID/update-status/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer RIDER_TOKEN' \
--data '{
    "status": "delivered",
    "notes": "Delivered successfully"
}'
```

**Expected Notifications:**
- ✅ Customer receives: "Your order #ORD-XXXXX has been delivered"
- ✅ Tailor receives: "Order #ORD-XXXXX has been delivered to customer"
- ✅ Rider receives: "Order #ORD-XXXXX delivery completed"

### 2.9 Cancel Order (Customer - only when status is pending)

```bash
curl --location --request PATCH 'YOUR_BASE_URL/api/orders/ORDER_ID/status/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer CUSTOMER_TOKEN' \
--data '{
    "status": "cancelled"
}'
```

**Expected Notifications:**
- ✅ Customer receives: "Your order #ORD-XXXXX has been cancelled"
- ✅ Tailor receives: "Order #ORD-XXXXX has been cancelled by customer"
- ✅ Rider receives: "Order #ORD-XXXXX has been cancelled" (if assigned)

---

## 3. Payment Status Notifications

### 3.1 Update Payment Status: pending → paid

```bash
curl --location --request PATCH 'YOUR_BASE_URL/api/orders/ORDER_ID/payment-status/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer CUSTOMER_TOKEN' \
--data '{
    "payment_status": "paid"
}'
```

**Expected Notifications:**
- ✅ Customer receives: "Payment of $X.XX received for order #ORD-XXXXX"
- ✅ Tailor receives: "Payment received for order #ORD-XXXXX - $X.XX"

### 3.2 Update Payment Status: paid → refunded

```bash
curl --location --request PATCH 'YOUR_BASE_URL/api/orders/ORDER_ID/payment-status/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer ADMIN_TOKEN' \
--data '{
    "payment_status": "refunded"
}'
```

**Expected Notifications:**
- ✅ Customer receives: "Refund of $X.XX has been processed for order #ORD-XXXXX"
- ✅ Tailor receives: "Refund issued for order #ORD-XXXXX"

---

## 4. Complete Test Flow (Fabric with Stitching)

### Step-by-step complete flow:

```bash
# Step 1: Register FCM tokens for all users
curl --location 'YOUR_BASE_URL/api/notifications/fcm-token/register/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer CUSTOMER_TOKEN' \
--data '{"token": "FCM_TOKEN_CUSTOMER", "device_type": "android"}'

curl --location 'YOUR_BASE_URL/api/notifications/fcm-token/register/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer TAILOR_TOKEN' \
--data '{"token": "FCM_TOKEN_TAILOR", "device_type": "android"}'

curl --location 'YOUR_BASE_URL/api/notifications/fcm-token/register/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer RIDER_TOKEN' \
--data '{"token": "FCM_TOKEN_RIDER", "device_type": "android"}'

# Step 2: Create order (Customer)
curl --location 'YOUR_BASE_URL/api/orders/create/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer CUSTOMER_TOKEN' \
--data '{
    "tailor": TAILOR_USER_ID,
    "order_type": "fabric_with_stitching",
    "payment_method": "credit_card",
    "delivery_address": ADDRESS_ID,
    "items": [{"fabric": FABRIC_ID, "quantity": 1}]
}'
# Save ORDER_ID from response

# Step 3: Tailor confirms order
curl --location --request PATCH 'YOUR_BASE_URL/api/orders/ORDER_ID/status/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer TAILOR_TOKEN' \
--data '{"status": "confirmed"}'

# Step 4: Customer pays
curl --location --request PATCH 'YOUR_BASE_URL/api/orders/ORDER_ID/payment-status/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer CUSTOMER_TOKEN' \
--data '{"payment_status": "paid"}'

# Step 5: Rider accepts order
curl --location 'YOUR_BASE_URL/api/riders/orders/ORDER_ID/accept/' \
--header 'Authorization: Bearer RIDER_TOKEN'

# Step 6: Rider adds measurements (optional - updates status to cutting)
curl --location --request POST 'YOUR_BASE_URL/api/riders/orders/ORDER_ID/measurements/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer RIDER_TOKEN' \
--data '{
    "rider_measurements": {
        "chest": "40",
        "waist": "32",
        "shoulder": "18"
    }
}'

# Step 7: Tailor updates to cutting
curl --location --request PATCH 'YOUR_BASE_URL/api/orders/ORDER_ID/status/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer TAILOR_TOKEN' \
--data '{"status": "cutting"}'

# Step 8: Tailor updates to stitching
curl --location --request PATCH 'YOUR_BASE_URL/api/orders/ORDER_ID/status/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer TAILOR_TOKEN' \
--data '{"status": "stitching"}'

# Step 9: Tailor marks ready for delivery
curl --location --request PATCH 'YOUR_BASE_URL/api/orders/ORDER_ID/status/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer TAILOR_TOKEN' \
--data '{"status": "ready_for_delivery"}'

# Step 10: Rider marks as delivered
curl --location --request PATCH 'YOUR_BASE_URL/api/riders/orders/ORDER_ID/update-status/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer RIDER_TOKEN' \
--data '{"status": "delivered", "notes": "Delivered successfully"}'

# Step 11: Check notification logs
curl --location 'YOUR_BASE_URL/api/notifications/logs/' \
--header 'Authorization: Bearer CUSTOMER_TOKEN'
```

---

## 5. Complete Test Flow (Fabric Only)

```bash
# Step 1: Create fabric_only order
curl --location 'YOUR_BASE_URL/api/orders/create/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer CUSTOMER_TOKEN' \
--data '{
    "tailor": TAILOR_USER_ID,
    "order_type": "fabric_only",
    "payment_method": "credit_card",
    "delivery_address": ADDRESS_ID,
    "items": [{"fabric": FABRIC_ID, "quantity": 1}]
}'

# Step 2: Tailor confirms
curl --location --request PATCH 'YOUR_BASE_URL/api/orders/ORDER_ID/status/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer TAILOR_TOKEN' \
--data '{"status": "confirmed"}'

# Step 3: Customer pays
curl --location --request PATCH 'YOUR_BASE_URL/api/orders/ORDER_ID/payment-status/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer CUSTOMER_TOKEN' \
--data '{"payment_status": "paid"}'

# Step 4: Rider accepts
curl --location 'YOUR_BASE_URL/api/riders/orders/ORDER_ID/accept/' \
--header 'Authorization: Bearer RIDER_TOKEN'

# Step 5: Rider marks ready for delivery
curl --location --request PATCH 'YOUR_BASE_URL/api/riders/orders/ORDER_ID/update-status/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer RIDER_TOKEN' \
--data '{"status": "ready_for_delivery"}'

# Step 6: Rider delivers
curl --location --request PATCH 'YOUR_BASE_URL/api/riders/orders/ORDER_ID/update-status/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer RIDER_TOKEN' \
--data '{"status": "delivered"}'
```

---

## 6. Testing Notification Logs

### 6.1 View Customer Notification Logs

```bash
curl --location 'YOUR_BASE_URL/api/notifications/logs/' \
--header 'Authorization: Bearer CUSTOMER_TOKEN'
```

### 6.2 View Tailor Notification Logs

```bash
curl --location 'YOUR_BASE_URL/api/notifications/logs/' \
--header 'Authorization: Bearer TAILOR_TOKEN'
```

### 6.3 View Rider Notification Logs

```bash
curl --location 'YOUR_BASE_URL/api/notifications/logs/' \
--header 'Authorization: Bearer RIDER_TOKEN'
```

---

## 7. Quick Test Script

Save this as `test_notifications.sh`:

```bash
#!/bin/bash

BASE_URL="YOUR_BASE_URL"
CUSTOMER_TOKEN="CUSTOMER_TOKEN"
TAILOR_TOKEN="TAILOR_TOKEN"
RIDER_TOKEN="RIDER_TOKEN"

echo "=== Testing Push Notifications ==="

echo "1. Registering FCM tokens..."
curl -s -X POST "$BASE_URL/api/notifications/fcm-token/register/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $CUSTOMER_TOKEN" \
  -d '{"token": "test_customer_token", "device_type": "android"}' | jq

echo "2. Creating order..."
ORDER_RESPONSE=$(curl -s -X POST "$BASE_URL/api/orders/create/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $CUSTOMER_TOKEN" \
  -d '{
    "tailor": TAILOR_USER_ID,
    "order_type": "fabric_with_stitching",
    "payment_method": "credit_card",
    "delivery_address": ADDRESS_ID,
    "items": [{"fabric": FABRIC_ID, "quantity": 1}]
  }')

ORDER_ID=$(echo $ORDER_RESPONSE | jq -r '.data.id')
echo "Order ID: $ORDER_ID"

echo "3. Tailor confirming order..."
curl -s -X PATCH "$BASE_URL/api/orders/$ORDER_ID/status/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TAILOR_TOKEN" \
  -d '{"status": "confirmed"}' | jq

echo "4. Checking notification logs..."
curl -s -X GET "$BASE_URL/api/notifications/logs/" \
  -H "Authorization: Bearer $CUSTOMER_TOKEN" | jq

echo "=== Test Complete ==="
```

---

## Expected Notification Counts

For a complete `fabric_with_stitching` order flow:

- **Customer**: ~8-10 notifications
  - Order created (pending)
  - Order confirmed
  - Payment received
  - Rider assigned
  - Measuring
  - Cutting
  - Stitching
  - Ready for delivery
  - Delivered

- **Tailor**: ~8-10 notifications
  - New order received
  - Order confirmed
  - Payment received
  - Rider assigned
  - Cutting
  - Stitching
  - Ready for pickup
  - Delivered

- **Rider**: ~4-5 notifications
  - Order assigned
  - Measuring (if fabric_with_stitching)
  - Ready for pickup
  - Delivered

---

## Troubleshooting

### No notifications received?

1. **Check FCM tokens are registered:**
   ```bash
   curl 'YOUR_BASE_URL/api/notifications/logs/' \
     -H "Authorization: Bearer CUSTOMER_TOKEN"
   ```

2. **Check Firebase configuration:**
   - Verify `FIREBASE_CREDENTIALS_PATH` in settings.py
   - Check Firebase credentials file exists
   - Verify Firebase project is active

3. **Check notification logs in Django Admin:**
   - Go to `/admin/notifications/notificationlog/`
   - Check for error messages

4. **Check Django logs:**
   ```bash
   tail -f logs/django.log | grep -i notification
   ```

### Invalid FCM token?

- Tokens are automatically deactivated if invalid
- Re-register token from mobile app
- Check `NotificationLog` for error details

---

## Notes

- Replace all placeholder values (`YOUR_BASE_URL`, `CUSTOMER_TOKEN`, etc.) with actual values
- FCM tokens should be real device tokens from Firebase SDK
- Order IDs, Fabric IDs, etc. should be from your database
- Notifications are sent asynchronously and won't block API responses
- All notification attempts are logged in `NotificationLog` model

