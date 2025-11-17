# Push Notifications - Quick Test Guide

## Quick Setup

Replace these values in the commands below:
- `YOUR_BASE_URL` = Your server URL (e.g., `http://69.62.126.95` or `http://localhost:8000`)
- `CUSTOMER_TOKEN` = JWT token from customer login
- `TAILOR_TOKEN` = JWT token from tailor login  
- `RIDER_TOKEN` = JWT token from rider login
- `ORDER_ID` = Order ID from create order response
- `FCM_TOKEN_*` = Real FCM device tokens (get from Firebase SDK in mobile app)

---

## Essential Test Commands

### 1. Register FCM Tokens (Do this first!)

**Customer:**
```bash
curl --location 'YOUR_BASE_URL/api/notifications/fcm-token/register/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer CUSTOMER_TOKEN' \
--data '{"token": "FCM_TOKEN_CUSTOMER", "device_type": "android"}'
```

**Tailor:**
```bash
curl --location 'YOUR_BASE_URL/api/notifications/fcm-token/register/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer TAILOR_TOKEN' \
--data '{"token": "FCM_TOKEN_TAILOR", "device_type": "android"}'
```

**Rider:**
```bash
curl --location 'YOUR_BASE_URL/api/notifications/fcm-token/register/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer RIDER_TOKEN' \
--data '{"token": "FCM_TOKEN_RIDER", "device_type": "android"}'
```

---

### 2. Test Order Status Notifications

**Create Order → Tailor gets "New order received"**
```bash
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
```

**Tailor Confirms → Customer gets "Order confirmed"**
```bash
curl --location --request PATCH 'YOUR_BASE_URL/api/orders/ORDER_ID/status/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer TAILOR_TOKEN' \
--data '{"status": "confirmed"}'
```

**Customer Pays → Both get "Payment received"**
```bash
curl --location --request PATCH 'YOUR_BASE_URL/api/orders/ORDER_ID/payment-status/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer CUSTOMER_TOKEN' \
--data '{"payment_status": "paid"}'
```

**Rider Accepts → All get "Rider assigned"**
```bash
curl --location 'YOUR_BASE_URL/api/riders/orders/ORDER_ID/accept/' \
--header 'Authorization: Bearer RIDER_TOKEN'
```

**Tailor Updates to Cutting → Customer gets notification**
```bash
curl --location --request PATCH 'YOUR_BASE_URL/api/orders/ORDER_ID/status/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer TAILOR_TOKEN' \
--data '{"status": "cutting"}'
```

**Tailor Updates to Stitching → Customer gets notification**
```bash
curl --location --request PATCH 'YOUR_BASE_URL/api/orders/ORDER_ID/status/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer TAILOR_TOKEN' \
--data '{"status": "stitching"}'
```

**Tailor Marks Ready → All get "Ready for delivery"**
```bash
curl --location --request PATCH 'YOUR_BASE_URL/api/orders/ORDER_ID/status/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer TAILOR_TOKEN' \
--data '{"status": "ready_for_delivery"}'
```

**Rider Delivers → All get "Order delivered"**
```bash
curl --location --request PATCH 'YOUR_BASE_URL/api/riders/orders/ORDER_ID/update-status/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer RIDER_TOKEN' \
--data '{"status": "delivered"}'
```

---

### 3. Check Notification Logs

**View all notifications sent to logged-in user:**
```bash
curl --location 'YOUR_BASE_URL/api/notifications/logs/' \
--header 'Authorization: Bearer CUSTOMER_TOKEN'
```

---

## Test Checklist

- [ ] Register FCM tokens for customer, tailor, and rider
- [ ] Create order → Check tailor receives notification
- [ ] Confirm order → Check customer receives notification
- [ ] Update payment to paid → Check both receive notifications
- [ ] Rider accepts order → Check all three receive notifications
- [ ] Update order statuses → Check relevant users receive notifications
- [ ] Mark as delivered → Check all receive notifications
- [ ] View notification logs → Verify all notifications were sent

---

## Expected Results

Each API call that changes order/payment status or assigns rider should:
1. ✅ Return success response
2. ✅ Send push notification(s) to relevant user(s)
3. ✅ Log notification attempt in database

Check notification logs to verify notifications were sent successfully!

