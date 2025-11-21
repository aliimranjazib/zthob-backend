# Fabric Only Order Flow - Complete API Guide

## Overview

This guide documents the complete API flow for `fabric_only` orders from customer creation to final delivery. 

**Order Type:** `fabric_only`  
**Status Flow:** `pending` → `confirmed` → `in_progress` → `ready_for_delivery` → `delivered`

---

## Prerequisites

### 1. Register FCM Tokens (Required for Notifications)

All users (Customer, Tailor, Rider) must register their FCM tokens to receive push notifications.

**Customer:**
```bash
curl --location 'http://localhost:8000/api/notifications/fcm-token/register/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer CUSTOMER_TOKEN' \
--data '{
    "token": "customer_fcm_token_here",
    "device_type": "android"
}'
```

**Tailor:**
```bash
curl --location 'http://localhost:8000/api/notifications/fcm-token/register/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer TAILOR_TOKEN' \
--data '{
    "token": "tailor_fcm_token_here",
    "device_type": "android"
}'
```

**Rider:**
```bash
curl --location 'http://localhost:8000/api/notifications/fcm-token/register/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer RIDER_TOKEN' \
--data '{
    "token": "rider_fcm_token_here",
    "device_type": "android"
}'
```

---

## Step-by-Step Flow

### Step 1: Customer Creates Order

**Endpoint:** `POST /api/orders/create/`

**Request:**
```bash
curl --location 'http://localhost:8000/api/orders/create/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer CUSTOMER_TOKEN' \
--data '{
    "tailor": 2,
    "order_type": "fabric_only",
    "payment_method": "credit_card",
    "delivery_address": 1,
    "items": [
        {
            "fabric": 5,
            "quantity": 2
        }
    ],
    "special_instructions": "Please handle with care",
    "distance_km": "8.5"
}'
```

**Response (201 Created):**
```json
{
    "success": true,
    "message": "Order created successfully",
    "data": {
        "id": 123,
        "order_number": "ORD-A1B2C3D4",
        "order_type": "fabric_only",
        "status": "pending",
        "rider_status": "none",
        "tailor_status": "none",
        "payment_status": "pending",
        "payment_method": "credit_card",
        "subtotal": "500.00",
        "tax_amount": "75.00",
        "delivery_fee": "25.00",
        "total_amount": "600.00",
        "customer": {
            "id": 1,
            "username": "customer_user",
            "email": "customer@example.com"
        },
        "tailor": {
            "id": 2,
            "username": "tailor_user",
            "email": "tailor@example.com"
        },
        "rider": null,
        "delivery_address": {
            "id": 1,
            "street": "123 Main St",
            "city": "Riyadh",
            "state_province": "Riyadh Province",
            "country": "Saudi Arabia"
        },
        "items": [
            {
                "id": 1,
                "fabric": {
                    "id": 5,
                    "name": "Premium Cotton",
                    "price": "250.00"
                },
                "quantity": 2,
                "unit_price": "250.00",
                "total_price": "500.00"
            }
        ],
        "special_instructions": "Please handle with care",
        "created_at": "2024-12-18T10:30:00Z",
        "updated_at": "2024-12-18T10:30:00Z"
    }
}
```

**What Happens:**
1. ✅ Order created with `status: "pending"`
2. ✅ `rider_status: "none"` (no rider assigned yet)
3. ✅ `tailor_status: "none"` (tailor hasn't accepted yet)
4. ✅ `payment_status: "pending"` (payment not completed)
5. ✅ Fabric stock is reduced by quantity
6. ✅ Order assigned to specified tailor
7. ✅ **Notification Sent to Tailor:**
   - Title: "New Order #ORD-A1B2C3D4"
   - Body: "New order #ORD-A1B2C3D4 received from customer_user"
   - Type: `ORDER_STATUS`
   - Category: `order_pending`
8. ✅ **Notification Sent to Customer:**
   - Title: "Order #ORD-A1B2C3D4 Created"
   - Body: "Your order #ORD-A1B2C3D4 has been placed successfully"
   - Type: `ORDER_STATUS`
   - Category: `order_pending`

---

### Step 2: Customer Updates Payment Status

**Endpoint:** `PATCH /api/orders/{order_id}/payment-status/`

**Request:**
```bash
curl --location --request PATCH 'http://localhost:8000/api/orders/123/payment-status/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer CUSTOMER_TOKEN' \
--data '{
    "payment_status": "paid"
}'
```

**Response (200 OK):**
```json
{
    "success": true,
    "message": "Payment status updated successfully",
    "data": {
        "id": 123,
        "order_number": "ORD-A1B2C3D4",
        "status": "pending",
        "payment_status": "paid",
        ...
    }
}
```

**What Happens:**
1. ✅ `payment_status` changed: `pending` → `paid`
2. ✅ Order status history updated
3. ✅ **Notification Sent to Tailor:**
   - Body: "Order #ORD-A1B2C3D4 payment received"
4. ✅ **Notification Sent to Customer:**
   - Body: "Payment for order #ORD-A1B2C3D4 confirmed"

**Note:** Payment must be `paid` before:
- Tailor can accept the order (recommended)
- Rider can accept the order (required)

---

### Step 3: Tailor Views Available Orders

**Endpoint:** `GET /api/orders/tailor/available-orders/`

**Request:**
```bash
curl --location 'http://localhost:8000/api/orders/tailor/available-orders/?order_type=fabric_only&payment_status=paid' \
--header 'Authorization: Bearer TAILOR_TOKEN'
```

**Response (200 OK):**
```json
{
    "success": true,
    "message": "Available orders retrieved successfully",
    "data": [
        {
            "id": 123,
            "order_number": "ORD-A1B2C3D4",
            "order_type": "fabric_only",
            "status": "pending",
            "tailor_status": "none",
            "payment_status": "paid",
            "total_amount": "600.00",
            "customer": {
                "id": 1,
                "username": "customer_user"
            },
            "items": [...]
        }
    ]
}
```

**What Happens:**
- Returns all orders assigned to tailor with:
  - `status: "pending"`
  - `tailor_status: "none"`
  - Optional filters: `order_type`, `payment_status`

---

### Step 4: Tailor Accepts Order

**Endpoint:** `PATCH /api/orders/{order_id}/status/`

**Request:**
```bash
curl --location --request PATCH 'http://localhost:8000/api/orders/123/status/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer TAILOR_TOKEN' \
--data '{
    "status": "confirmed",
    "tailor_status": "accepted",
    "notes": "Order accepted, will prepare fabric"
}'
```

**Response (200 OK):**
```json
{
    "success": true,
    "message": "Order status updated successfully",
    "data": {
        "id": 123,
        "order_number": "ORD-A1B2C3D4",
        "status": "confirmed",
        "rider_status": "none",
        "tailor_status": "accepted",
        "status_info": {
            "current_status": "confirmed",
            "current_rider_status": "none",
            "current_tailor_status": "accepted",
            "next_allowed_statuses": {
                "status": ["in_progress"],
                "rider_status": [],
                "tailor_status": []
            }
        },
        "updated_at": "2024-12-18T11:00:00Z"
    }
}
```

**What Happens:**
1. ✅ `status` changed: `pending` → `confirmed`
2. ✅ `tailor_status` changed: `none` → `accepted`
3. ✅ Order status history entry created
4. ✅ **Notification Sent to Customer:**
   - Title: "Order #ORD-A1B2C3D4 Accepted"
   - Body: "Tailor has accepted your order #ORD-A1B2C3D4"
   - Type: `ORDER_STATUS`
   - Category: `order_confirmed`

**Important:** 
- Once `status: "confirmed"`, order can no longer be cancelled by customer
- Order is now ready for rider assignment

---

### Step 5: Rider Views Available Orders

**Endpoint:** `GET /api/riders/orders/available/`

**Request:**
```bash
curl --location 'http://localhost:8000/api/riders/orders/available/?order_type=fabric_only' \
--header 'Authorization: Bearer RIDER_TOKEN'
```

**Response (200 OK):**
```json
{
    "success": true,
    "message": "Available orders retrieved successfully",
    "data": [
        {
            "id": 123,
            "order_number": "ORD-A1B2C3D4",
            "order_type": "fabric_only",
            "status": "confirmed",
            "rider_status": "none",
            "payment_status": "paid",
            "total_amount": "600.00",
            "delivery_address": {
                "street": "123 Main St",
                "city": "Riyadh"
            },
            "pickup_address": {
                "shop_name": "ABC Tailor Shop",
                "address": "456 Tailor St"
            }
        }
    ]
}
```

**What Happens:**
- Returns orders available for rider assignment with:
  - `payment_status: "paid"` (required)
  - `status: "confirmed"` or `"in_progress"` or `"ready_for_delivery"` (not `pending`)
  - `rider_status: "none"` (not yet assigned)
  - Rider must be approved (`is_approved: true`)

---

### Step 6: Rider Accepts Order

**Endpoint:** `POST /api/riders/orders/{order_id}/accept/`

**Request:**
```bash
curl --location --request POST 'http://localhost:8000/api/riders/orders/123/accept/' \
--header 'Authorization: Bearer RIDER_TOKEN'
```

**Response (200 OK):**
```json
{
    "success": true,
    "message": "Order accepted successfully",
    "data": {
        "id": 123,
        "order_number": "ORD-A1B2C3D4",
        "status": "confirmed",
        "rider_status": "accepted",
        "rider": {
            "id": 3,
            "username": "rider_user"
        },
        ...
    }
}
```

**What Happens:**
1. ✅ `rider` field assigned to rider user
2. ✅ `rider_status` changed: `none` → `accepted`
3. ✅ `RiderOrderAssignment` record created
4. ✅ **Notification Sent to Customer:**
   - Body: "Rider assigned to your order #ORD-A1B2C3D4"
5. ✅ **Notification Sent to Tailor:**
   - Body: "Rider assigned to order #ORD-A1B2C3D4"
6. ✅ **Notification Sent to Rider:**
   - Body: "Order #ORD-A1B2C3D4 accepted successfully"

**Requirements:**
- Order `payment_status` must be `paid`
- Order `status` must NOT be `pending` (must be `confirmed` or beyond)
- Rider must be approved
- Order must not already have a rider assigned

---

### Step 7: Tailor Marks Order Ready (Optional but Recommended)

**Endpoint:** `PATCH /api/orders/{order_id}/status/`

**Request:**
```bash
curl --location --request PATCH 'http://localhost:8000/api/orders/123/status/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer TAILOR_TOKEN' \
--data '{
    "status": "in_progress",
    "notes": "Fabric prepared and ready for pickup"
}'
```

**Response (200 OK):**
```json
{
    "success": true,
    "message": "Order status updated successfully",
    "data": {
        "id": 123,
        "order_number": "ORD-A1B2C3D4",
        "status": "in_progress",
        "rider_status": "accepted",
        "tailor_status": "accepted",
        ...
    }
}
```

**What Happens:**
1. ✅ `status` changed: `confirmed` → `in_progress`
2. ✅ **Notification Sent to Customer:**
   - Body: "Your order #ORD-A1B2C3D4 is being prepared"
3. ✅ **Notification Sent to Rider:**
   - Body: "Order #ORD-A1B2C3D4 is ready for pickup"

**Note:** This step is optional. The system will auto-sync status to `in_progress` when rider updates status to `on_way_to_pickup`.

---

### Step 8: Rider Updates Status - On Way to Pickup

**Endpoint:** `PATCH /api/riders/orders/{order_id}/update-status/`

**Request:**
```bash
curl --location --request PATCH 'http://localhost:8000/api/riders/orders/123/update-status/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer RIDER_TOKEN' \
--data '{
    "rider_status": "on_way_to_pickup",
    "notes": "On my way to pickup from tailor"
}'
```

**Response (200 OK):**
```json
{
    "success": true,
    "message": "Order rider status updated to On Way to Pickup",
    "data": {
        "id": 123,
        "order_number": "ORD-A1B2C3D4",
        "status": "in_progress",
        "rider_status": "on_way_to_pickup",
        ...
    }
}
```

**What Happens:**
1. ✅ `rider_status` changed: `accepted` → `on_way_to_pickup`
2. ✅ Main `status` auto-synced: `confirmed` → `in_progress` (if not already)
3. ✅ **Notification Sent to Customer:**
   - Body: "Rider is on the way to pickup your order #ORD-A1B2C3D4"
4. ✅ **Notification Sent to Tailor:**
   - Body: "Rider is on the way to pickup order #ORD-A1B2C3D4"

---

### Step 9: Rider Updates Status - Picked Up

**Endpoint:** `PATCH /api/riders/orders/{order_id}/update-status/`

**Request:**
```bash
curl --location --request PATCH 'http://localhost:8000/api/riders/orders/123/update-status/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer RIDER_TOKEN' \
--data '{
    "rider_status": "picked_up",
    "notes": "Order picked up from tailor shop"
}'
```

**Response (200 OK):**
```json
{
    "success": true,
    "message": "Order rider status updated to Picked Up",
    "data": {
        "id": 123,
        "order_number": "ORD-A1B2C3D4",
        "status": "ready_for_delivery",
        "rider_status": "picked_up",
        ...
    }
}
```

**What Happens:**
1. ✅ `rider_status` changed: `on_way_to_pickup` → `picked_up`
2. ✅ Main `status` auto-synced: `in_progress` → `ready_for_delivery`
3. ✅ **Notification Sent to Customer:**
   - Body: "Your order #ORD-A1B2C3D4 has been picked up and is ready for delivery"
4. ✅ **Notification Sent to Tailor:**
   - Body: "Order #ORD-A1B2C3D4 has been picked up by rider"

---

### Step 10: Rider Updates Status - On Way to Delivery

**Endpoint:** `PATCH /api/riders/orders/{order_id}/update-status/`

**Request:**
```bash
curl --location --request PATCH 'http://localhost:8000/api/riders/orders/123/update-status/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer RIDER_TOKEN' \
--data '{
    "rider_status": "on_way_to_delivery",
    "notes": "On my way to deliver to customer"
}'
```

**Response (200 OK):**
```json
{
    "success": true,
    "message": "Order rider status updated to On Way to Delivery",
    "data": {
        "id": 123,
        "order_number": "ORD-A1B2C3D4",
        "status": "ready_for_delivery",
        "rider_status": "on_way_to_delivery",
        ...
    }
}
```

**What Happens:**
1. ✅ `rider_status` changed: `picked_up` → `on_way_to_delivery`
2. ✅ Main `status` remains: `ready_for_delivery`
3. ✅ **Notification Sent to Customer:**
   - Body: "Rider is on the way to deliver your order #ORD-A1B2C3D4"
4. ✅ **Notification Sent to Tailor:**
   - Body: "Order #ORD-A1B2C3D4 is on the way to customer"

---

### Step 11: Rider Updates Status - Delivered (FINAL STEP)

**Endpoint:** `PATCH /api/riders/orders/{order_id}/update-status/`

**Request:**
```bash
curl --location --request PATCH 'http://localhost:8000/api/riders/orders/123/update-status/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer RIDER_TOKEN' \
--data '{
    "rider_status": "delivered",
    "notes": "Order delivered successfully to customer"
}'
```

**Response (200 OK):**
```json
{
    "success": true,
    "message": "Order rider status updated to Delivered",
    "data": {
        "id": 123,
        "order_number": "ORD-A1B2C3D4",
        "status": "delivered",
        "rider_status": "delivered",
        "actual_delivery_date": "2024-12-18",
        ...
    }
}
```

**What Happens:**
1. ✅ `rider_status` changed: `on_way_to_delivery` → `delivered`
2. ✅ Main `status` changed: `ready_for_delivery` → `delivered` (automatic)
3. ✅ `actual_delivery_date` set to today
4. ✅ `RiderOrderAssignment` marked as `completed`
5. ✅ Rider statistics updated (`total_deliveries += 1`)
6. ✅ **Notification Sent to Customer:**
   - Title: "Order #ORD-A1B2C3D4 Delivered"
   - Body: "Your order #ORD-A1B2C3D4 has been delivered"
   - Type: `ORDER_STATUS`
   - Category: `order_delivered`
7. ✅ **Notification Sent to Tailor:**
   - Body: "Order #ORD-A1B2C3D4 has been delivered to customer"
8. ✅ **Notification Sent to Rider:**
   - Body: "Order #ORD-A1B2C3D4 delivery completed"

**Order Status:** `delivered` (FINAL STATE - no further changes allowed)

---

## Complete Status Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    FABRIC_ONLY ORDER FLOW                        │
└─────────────────────────────────────────────────────────────────┘

Step 1: Customer Creates Order
┌─────────────────────────────────────┐
│ Order: pending                      │
│ rider_status: none                  │
│ tailor_status: none                 │
│ payment_status: pending              │
│ 🔔 Notify: Customer + Tailor        │
└─────────────────────────────────────┘
              ↓
Step 2: Customer Updates Payment
┌─────────────────────────────────────┐
│ Order: pending                      │
│ payment_status: paid                │
│ 🔔 Notify: Customer + Tailor        │
└─────────────────────────────────────┘
              ↓
Step 3: Tailor Accepts Order
┌─────────────────────────────────────┐
│ Order: confirmed                    │
│ tailor_status: accepted             │
│ 🔔 Notify: Customer                 │
└─────────────────────────────────────┘
              ↓
Step 4: Rider Accepts Order
┌─────────────────────────────────────┐
│ Order: confirmed                    │
│ rider_status: accepted              │
│ rider: [rider_user]                 │
│ 🔔 Notify: Customer + Tailor + Rider│
└─────────────────────────────────────┘
              ↓
Step 5: Rider On Way to Pickup
┌─────────────────────────────────────┐
│ Order: in_progress                  │
│ rider_status: on_way_to_pickup      │
│ 🔔 Notify: Customer + Tailor        │
└─────────────────────────────────────┘
              ↓
Step 6: Rider Picked Up
┌─────────────────────────────────────┐
│ Order: ready_for_delivery           │
│ rider_status: picked_up              │
│ 🔔 Notify: Customer + Tailor        │
└─────────────────────────────────────┘
              ↓
Step 7: Rider On Way to Delivery
┌─────────────────────────────────────┐
│ Order: ready_for_delivery           │
│ rider_status: on_way_to_delivery     │
│ 🔔 Notify: Customer + Tailor        │
└─────────────────────────────────────┘
              ↓
Step 8: Rider Delivered (FINAL)
┌─────────────────────────────────────┐
│ Order: delivered                    │
│ rider_status: delivered              │
│ actual_delivery_date: [today]       │
│ 🔔 Notify: Customer + Tailor + Rider│
└─────────────────────────────────────┘
```

---

## Status Transition Rules

### Allowed Transitions for Fabric Only Orders

| Current Status | Current Rider Status | Next Rider Status | Next Main Status | Who Can Update |
|----------------|---------------------|-------------------|------------------|----------------|
| `pending` | `none` | - | `confirmed` | TAILOR |
| `pending` | `none` | - | `cancelled` | USER (customer) |
| `confirmed` | `none` | `accepted` | `confirmed` | RIDER |
| `confirmed` | `accepted` | `on_way_to_pickup` | `in_progress` | RIDER |
| `in_progress` | `on_way_to_pickup` | `picked_up` | `ready_for_delivery` | RIDER |
| `ready_for_delivery` | `picked_up` | `on_way_to_delivery` | `ready_for_delivery` | RIDER |
| `ready_for_delivery` | `on_way_to_delivery` | `delivered` | `delivered` | RIDER |

### Role-Based Permissions

- **CUSTOMER (USER):**
  - Can only cancel orders when `status: "pending"`
  - Can update payment status
  - Can view their own orders

- **TAILOR:**
  - Can accept orders (`pending` → `confirmed`)
  - Can update status to `in_progress` (optional)
  - Cannot cancel orders
  - Can view orders assigned to them

- **RIDER:**
  - Can accept orders (when `payment_status: "paid"` and `status: "confirmed"` or beyond)
  - Can update `rider_status` through the flow
  - Can mark order as `delivered` (final step)
  - Must be approved to accept orders

- **ADMIN:**
  - Can do everything (full control)

---

## Key API Endpoints Summary

### Customer Endpoints
- `POST /api/orders/create/` - Create order
- `PATCH /api/orders/{order_id}/payment-status/` - Update payment status
- `GET /api/orders/customer/my-orders/` - View my orders
- `GET /api/orders/{order_id}/` - View order details
- `GET /api/orders/{order_id}/history/` - View order history

### Tailor Endpoints
- `GET /api/orders/tailor/available-orders/` - View pending orders
- `GET /api/orders/tailor/my-orders/` - View accepted orders
- `GET /api/orders/tailor/{order_id}/` - View order details
- `PATCH /api/orders/{order_id}/status/` - Update order status

### Rider Endpoints
- `GET /api/riders/orders/available/` - View available orders
- `GET /api/riders/orders/my-orders/` - View my assigned orders
- `GET /api/riders/orders/{order_id}/` - View order details
- `POST /api/riders/orders/{order_id}/accept/` - Accept order
- `PATCH /api/riders/orders/{order_id}/update-status/` - Update rider status

---

## Important Notes

1. **Payment Status:** Order `payment_status` must be `paid` before rider can accept the order.

2. **Status Auto-Sync:** The main `status` automatically syncs based on `rider_status`:
   - When `rider_status: "on_way_to_pickup"` → `status: "in_progress"`
   - When `rider_status: "picked_up"` → `status: "ready_for_delivery"`
   - When `rider_status: "delivered"` → `status: "delivered"`

3. **Cancellation:** Orders can only be cancelled when `status: "pending"` and only by the customer.

4. **Final States:** Once `status: "delivered"` or `status: "cancelled"`, no further changes are allowed.

5. **Notifications:** All status changes trigger push notifications to relevant parties (customer, tailor, rider).

6. **Order History:** All status changes are tracked in `OrderStatusHistory` for audit purposes.

---

## Error Scenarios

### Common Errors

1. **Rider tries to accept order with `payment_status: "pending"`**
   - Error: "Order payment must be paid before rider can accept it"
   - Solution: Customer must update payment status first

2. **Rider tries to accept order with `status: "pending"`**
   - Error: "Order is still pending tailor confirmation"
   - Solution: Tailor must accept the order first

3. **Customer tries to cancel order with `status: "confirmed"`**
   - Error: "Orders can only be cancelled when status is pending"
   - Solution: Cannot cancel after tailor acceptance

4. **Invalid status transition**
   - Error: "Cannot change status from X to Y. Allowed: [list]"
   - Solution: Follow the allowed transition flow

---

## Testing the Flow

### Quick Test Sequence

1. **Create Order:**
   ```bash
   POST /api/orders/create/
   # Save order_id from response
   ```

2. **Update Payment:**
   ```bash
   PATCH /api/orders/{order_id}/payment-status/
   ```

3. **Tailor Accepts:**
   ```bash
   PATCH /api/orders/{order_id}/status/
   # status: "confirmed", tailor_status: "accepted"
   ```

4. **Rider Accepts:**
   ```bash
   POST /api/riders/orders/{order_id}/accept/
   ```

5. **Rider Updates Status:**
   ```bash
   PATCH /api/riders/orders/{order_id}/update-status/
   # rider_status: "on_way_to_pickup"
   # rider_status: "picked_up"
   # rider_status: "on_way_to_delivery"
   # rider_status: "delivered"
   ```

---

## Next Steps

After completing the `fabric_only` flow, you can:
1. Test the complete flow end-to-end
2. Implement the `fabric_with_stitching` flow (similar but with measurement steps)
3. Add error handling and edge cases
4. Implement order tracking UI in frontend

---

**Last Updated:** 2024-12-18  
**Version:** 1.0

