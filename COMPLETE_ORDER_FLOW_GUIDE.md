# Complete Order Flow Guide - From Creation to Delivery

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Order Creation Flow](#order-creation-flow)
3. [Fabric Only Flow](#fabric-only-flow)
4. [Fabric With Stitching Flow](#fabric-with-stitching-flow)
5. [Status Transition APIs](#status-transition-apis)
6. [Notification System](#notification-system)
7. [Error Handling](#error-handling)
8. [Complete Flow Diagrams](#complete-flow-diagrams)

---

## Prerequisites

### 1. Register FCM Tokens (Required for Notifications)

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

**Response:**
```json
{
    "success": true,
    "message": "FCM token registered successfully",
    "data": {
        "id": 1,
        "token": "customer_fcm_token_here",
        "device_type": "android",
        "is_active": true
    }
}
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

## Order Creation Flow

### Step 1: Customer Creates Order

**Endpoint:** `POST /api/orders/create/`

**Request:**
```bash
curl --location 'http://localhost:8000/api/orders/create/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer CUSTOMER_TOKEN' \
--data '{
    "tailor": 2,
    "order_type": "fabric_with_stitching",
    "payment_method": "credit_card",
    "delivery_address": 1,
    "items": [
        {
            "fabric": 5,
            "quantity": 2
        }
    ],
    "special_instructions": "Please make it extra comfortable",
    "appointment_date": "2024-12-20",
    "appointment_time": "14:00:00",
    "custom_styles": [
        {
            "style_type": "collar",
            "index": 0,
            "label": "Collar Style 1",
            "asset_path": "assets/thobs/collar/collar1.png"
        }
    ]
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
        "order_type": "fabric_with_stitching",
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
        "special_instructions": "Please make it extra comfortable",
        "appointment_date": "2024-12-20",
        "appointment_time": "14:00:00",
        "custom_styles": [
            {
                "style_type": "collar",
                "index": 0,
                "label": "Collar Style 1",
                "asset_path": "assets/thobs/collar/collar1.png"
            }
        ],
        "created_at": "2024-12-18T10:30:00Z",
        "updated_at": "2024-12-18T10:30:00Z"
    }
}
```

**What Happens:**
1. ✅ Order created with status `pending`
2. ✅ `rider_status` set to `none`
3. ✅ `tailor_status` set to `none`
4. ✅ Order assigned to tailor
5. ✅ **Notification Sent to Tailor:**
   - Title: "Order #ORD-A1B2C3D4 Update"
   - Body: "New order #ORD-A1B2C3D4 received from customer_user"
   - Type: `ORDER_STATUS`
   - Category: `order_pending`
   - Data: `{"order_id": 123, "order_number": "ORD-A1B2C3D4", "status": "pending"}`

6. ✅ **Notification Sent to Customer:**
   - Title: "Order #ORD-A1B2C3D4 Update"
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
        "payment_status": "paid",
        "total_amount": "600.00",
        ...
    }
}
```

**What Happens:**
1. ✅ Payment status updated to `paid`
2. ✅ **Notification Sent to Customer:**
   - Title: "Payment Update"
   - Body: "Payment of 600.00 received for order #ORD-A1B2C3D4"
   - Type: `PAYMENT`
   - Category: `payment_paid`

3. ✅ **Notification Sent to Tailor:**
   - Title: "Payment Update"
   - Body: "Payment received for order #ORD-A1B2C3D4 - 600.00"
   - Type: `PAYMENT`
   - Category: `payment_paid`

---

## Fabric Only Flow

### Step 1: Tailor Accepts Order

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
        "notes": "Order accepted, will prepare fabric",
        ...
    }
}
```

**What Happens:**
1. ✅ Order status changed: `pending` → `confirmed`
2. ✅ Tailor status changed: `none` → `accepted`
3. ✅ Status history created
4. ✅ **Notification Sent to Customer:**
   - Title: "Order #ORD-A1B2C3D4 Update"
   - Body: "Tailor has accepted your order #ORD-A1B2C3D4"
   - Type: `ORDER_STATUS`
   - Category: `order_confirmed`
   - Data: `{"order_id": 123, "status": "confirmed", "old_status": "pending"}`

5. ✅ **Notification Sent to Tailor:**
   - Title: "Order #ORD-A1B2C3D4 Update"
   - Body: "You have confirmed order #ORD-A1B2C3D4"
   - Type: `ORDER_STATUS`
   - Category: `order_confirmed`

---

### Step 2: Tailor Marks Order In Progress

**Request:**
```bash
curl --location --request PATCH 'http://localhost:8000/api/orders/123/status/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer TAILOR_TOKEN' \
--data '{
    "status": "in_progress",
    "notes": "Preparing fabric for packaging"
}'
```

**Response:**
```json
{
    "success": true,
    "message": "Order status updated successfully",
    "data": {
        "id": 123,
        "status": "in_progress",
        ...
    }
}
```

**Notifications:** Customer and Tailor notified of status change

---

### Step 3: Tailor Marks Ready for Delivery

**Request:**
```bash
curl --location --request PATCH 'http://localhost:8000/api/orders/123/status/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer TAILOR_TOKEN' \
--data '{
    "status": "ready_for_delivery",
    "notes": "Order packaged and ready for pickup"
}'
```

**Response:**
```json
{
    "success": true,
    "message": "Order status updated successfully",
    "data": {
        "id": 123,
        "status": "ready_for_delivery",
        ...
    }
}
```

**What Happens:**
1. ✅ Status changed: `in_progress` → `ready_for_delivery`
2. ✅ **Notification Sent to Customer:**
   - Body: "Your order #ORD-A1B2C3D4 is ready for delivery"

3. ✅ **Notification Sent to Tailor:**
   - Body: "Order #ORD-A1B2C3D4 is ready for pickup"

4. ✅ **Notification Sent to Rider (if assigned):**
   - Body: "Order #ORD-A1B2C3D4 is ready for pickup from tailor"

---

### Step 4: Rider Views Available Orders

**Endpoint:** `GET /api/riders/orders/available/`

**Request:**
```bash
curl --location 'http://localhost:8000/api/riders/orders/available/?status=confirmed&order_type=fabric_only' \
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
            "tailor_status": "accepted",
            "payment_status": "paid",
            "total_amount": "600.00",
            "customer_name": "customer_user",
            "customer_phone": "+966501234567",
            "tailor_name": "Tailor Shop Name",
            "tailor_phone": "+966509876543",
            "delivery_address": "123 Main St, Riyadh, Saudi Arabia",
            "items_count": 1,
            "created_at": "2024-12-18T10:30:00Z"
        }
    ]
}
```

**Note:** Riders can only see orders with:
- `payment_status = 'paid'`
- `rider = null` (not assigned)
- `status != 'pending'` (tailor must have accepted)

---

### Step 5: Rider Accepts Order

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
        "tailor_status": "accepted",
        "rider": {
            "id": 3,
            "username": "rider_user",
            "email": "rider@example.com"
        },
        ...
    }
}
```

**What Happens:**
1. ✅ Rider assigned to order
2. ✅ `rider_status` changed: `none` → `accepted`
3. ✅ Rider assignment record created
4. ✅ **Notification Sent to Customer:**
   - Title: "Rider Assigned"
   - Body: "Rider rider_user has been assigned to deliver your order #ORD-A1B2C3D4"
   - Type: `RIDER_ASSIGNMENT`
   - Category: `rider_assigned`
   - Data: `{"order_id": 123, "rider_id": 3, "rider_name": "rider_user"}`

5. ✅ **Notification Sent to Tailor:**
   - Title: "Rider Assigned"
   - Body: "Rider rider_user will pick up order #ORD-A1B2C3D4"
   - Type: `RIDER_ASSIGNMENT`
   - Category: `rider_assigned`

6. ✅ **Notification Sent to Rider:**
   - Title: "New Order Assignment"
   - Body: "You have been assigned to order #ORD-A1B2C3D4"
   - Type: `RIDER_ASSIGNMENT`
   - Category: `order_assigned`

---

### Step 6: Rider Updates Status - On Way to Pickup

**Endpoint:** `PATCH /api/riders/orders/{order_id}/status/`

**Request:**
```bash
curl --location --request PATCH 'http://localhost:8000/api/riders/orders/123/status/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer RIDER_TOKEN' \
--data '{
    "rider_status": "on_way_to_pickup",
    "notes": "On my way to pickup order from tailor"
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
        "tailor_status": "accepted",
        ...
    }
}
```

**What Happens:**
1. ✅ `rider_status` changed: `accepted` → `on_way_to_pickup`
2. ✅ Main `status` auto-synced: `confirmed` → `in_progress` (automatic)
3. ✅ Status history created
4. ✅ **Notifications sent to Customer, Tailor, and Rider**

---

### Step 7: Rider Updates Status - Picked Up

**Request:**
```bash
curl --location --request PATCH 'http://localhost:8000/api/riders/orders/123/status/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer RIDER_TOKEN' \
--data '{
    "rider_status": "picked_up",
    "notes": "Order picked up from tailor shop"
}'
```

**Response:**
```json
{
    "success": true,
    "message": "Order rider status updated to Picked Up",
    "data": {
        "id": 123,
        "status": "ready_for_delivery",
        "rider_status": "picked_up",
        ...
    }
}
```

**What Happens:**
1. ✅ `rider_status` changed: `on_way_to_pickup` → `picked_up`
2. ✅ Main `status` auto-synced: `in_progress` → `ready_for_delivery` (automatic)
3. ✅ **Notifications sent**

---

### Step 8: Rider Updates Status - On Way to Delivery

**Request:**
```bash
curl --location --request PATCH 'http://localhost:8000/api/riders/orders/123/status/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer RIDER_TOKEN' \
--data '{
    "rider_status": "on_way_to_delivery",
    "notes": "On my way to customer location"
}'
```

**Response:**
```json
{
    "success": true,
    "message": "Order rider status updated to On Way to Delivery",
    "data": {
        "id": 123,
        "status": "ready_for_delivery",
        "rider_status": "on_way_to_delivery",
        ...
    }
}
```

---

### Step 9: Rider Updates Status - Delivered

**Request:**
```bash
curl --location --request PATCH 'http://localhost:8000/api/riders/orders/123/status/' \
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
        "tailor_status": "accepted",
        "actual_delivery_date": "2024-12-18",
        ...
    }
}
```

**What Happens:**
1. ✅ `rider_status` changed: `on_way_to_delivery` → `delivered`
2. ✅ Main `status` changed: `ready_for_delivery` → `delivered` (automatic)
3. ✅ `actual_delivery_date` set to today
4. ✅ Rider assignment marked as `completed`
5. ✅ Rider statistics updated (`total_deliveries += 1`)
6. ✅ **Notification Sent to Customer:**
   - Title: "Order #ORD-A1B2C3D4 Update"
   - Body: "Your order #ORD-A1B2C3D4 has been delivered"
   - Type: `ORDER_STATUS`
   - Category: `order_delivered`

7. ✅ **Notification Sent to Tailor:**
   - Body: "Order #ORD-A1B2C3D4 has been delivered to customer"

8. ✅ **Notification Sent to Rider:**
   - Body: "Order #ORD-A1B2C3D4 delivery completed"

---

## Fabric With Stitching Flow

### Step 1: Tailor Accepts Order

**Same as Fabric Only - Step 1**

---

### Step 2: Rider Accepts Order

**Same as Fabric Only - Step 4**

---

### Step 3: Rider Updates Status - On Way to Measurement

**Endpoint:** `PATCH /api/riders/orders/{order_id}/status/`

**Request:**
```bash
curl --location --request PATCH 'http://localhost:8000/api/riders/orders/123/status/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer RIDER_TOKEN' \
--data '{
    "rider_status": "on_way_to_measurement",
    "notes": "On my way to take customer measurements"
}'
```

**Response:**
```json
{
    "success": true,
    "message": "Order rider status updated to On Way to Measurement",
    "data": {
        "id": 123,
        "status": "in_progress",
        "rider_status": "on_way_to_measurement",
        ...
    }
}
```

**What Happens:**
1. ✅ `rider_status` changed: `accepted` → `on_way_to_measurement`
2. ✅ Main `status` auto-synced: `confirmed` → `in_progress`
3. ✅ **Notification Sent to Customer:**
   - Body: "Rider is on the way to take your measurements for order #ORD-A1B2C3D4"

---

### Step 4: Rider Takes Measurements

**Endpoint:** `POST /api/riders/orders/{order_id}/measurements/`

**Request:**
```bash
curl --location --request POST 'http://localhost:8000/api/riders/orders/123/measurements/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer RIDER_TOKEN' \
--data '{
    "measurements": {
        "chest": "40",
        "waist": "36",
        "shoulder": "18",
        "sleeve_length": "24",
        "length": "42",
        "neck": "16"
    },
    "notes": "Measurements taken successfully"
}'
```

**Response (200 OK):**
```json
{
    "success": true,
    "message": "Measurements added successfully. Tailor can now proceed with cutting.",
    "data": {
        "id": 123,
        "order_number": "ORD-A1B2C3D4",
        "status": "in_progress",
        "rider_status": "measurement_taken",
        "tailor_status": "accepted",
        "rider_measurements": {
            "chest": "40",
            "waist": "36",
            "shoulder": "18",
            "sleeve_length": "24",
            "length": "42",
            "neck": "16"
        },
        "measurement_taken_at": "2024-12-18T11:30:00Z",
        ...
    }
}
```

**What Happens:**
1. ✅ `rider_status` changed: `on_way_to_measurement` → `measurement_taken`
2. ✅ Measurements stored in `rider_measurements` field
3. ✅ `measurement_taken_at` timestamp set
4. ✅ Rider assignment status updated to `in_progress`
5. ✅ **Notification Sent to Customer:**
   - Body: "Measurements taken for order #ORD-A1B2C3D4"

6. ✅ **Notification Sent to Tailor:**
   - Body: "Measurements ready for order #ORD-A1B2C3D4 - you can start stitching"

---

### Step 5: Tailor Starts Stitching

**Endpoint:** `PATCH /api/orders/{order_id}/status/`

**Request:**
```bash
curl --location --request PATCH 'http://localhost:8000/api/orders/123/status/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer TAILOR_TOKEN' \
--data '{
    "tailor_status": "stitching_started",
    "notes": "Started stitching the garment"
}'
```

**Response (200 OK):**
```json
{
    "success": true,
    "message": "Order status updated successfully",
    "data": {
        "id": 123,
        "status": "in_progress",
        "rider_status": "measurement_taken",
        "tailor_status": "stitching_started",
        ...
    }
}
```

**What Happens:**
1. ✅ `tailor_status` changed: `accepted` → `stitching_started`
2. ✅ **Notification Sent to Customer:**
   - Title: "Order #ORD-A1B2C3D4 Update"
   - Body: "Your garment is being stitched for order #ORD-A1B2C3D4"
   - Type: `ORDER_STATUS`
   - Category: `order_stitching`

3. ✅ **Notification Sent to Tailor:**
   - Body: "Order #ORD-A1B2C3D4 is ready for stitching"

---

### Step 6: Tailor Finishes Stitching

**Request:**
```bash
curl --location --request PATCH 'http://localhost:8000/api/orders/123/status/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer TAILOR_TOKEN' \
--data '{
    "tailor_status": "stitched",
    "status": "ready_for_delivery",
    "notes": "Stitching completed, ready for pickup"
}'
```

**Response:**
```json
{
    "success": true,
    "message": "Order status updated successfully",
    "data": {
        "id": 123,
        "status": "ready_for_delivery",
        "rider_status": "measurement_taken",
        "tailor_status": "stitched",
        ...
    }
}
```

**What Happens:**
1. ✅ `tailor_status` changed: `stitching_started` → `stitched`
2. ✅ Main `status` changed: `in_progress` → `ready_for_delivery`
3. ✅ **Notification Sent to Customer:**
   - Body: "Your order #ORD-A1B2C3D4 is ready for delivery"

4. ✅ **Notification Sent to Tailor:**
   - Body: "Order #ORD-A1B2C3D4 is ready for pickup"

5. ✅ **Notification Sent to Rider:**
   - Body: "Order #ORD-A1B2C3D4 is ready for pickup from tailor"

---

### Step 7: Rider Updates Status - On Way to Pickup

**Request:**
```bash
curl --location --request PATCH 'http://localhost:8000/api/riders/orders/123/status/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer RIDER_TOKEN' \
--data '{
    "rider_status": "on_way_to_pickup",
    "notes": "On my way to pickup stitched garment"
}'
```

**Response:**
```json
{
    "success": true,
    "message": "Order rider status updated to On Way to Pickup",
    "data": {
        "id": 123,
        "status": "ready_for_delivery",
        "rider_status": "on_way_to_pickup",
        "tailor_status": "stitched",
        ...
    }
}
```

**Note:** Rider can only proceed to `on_way_to_pickup` when `tailor_status = 'stitched'`

---

### Step 8-10: Same as Fabric Only Steps 7-9

- Rider Picked Up
- Rider On Way to Delivery
- Rider Delivered

---

## Status Transition APIs

### Get Order Details

**Endpoint:** `GET /api/orders/{order_id}/`

**Request:**
```bash
curl --location 'http://localhost:8000/api/orders/123/' \
--header 'Authorization: Bearer CUSTOMER_TOKEN'
```

**Response:**
```json
{
    "success": true,
    "message": "Order retrieved successfully",
    "data": {
        "id": 123,
        "order_number": "ORD-A1B2C3D4",
        "order_type": "fabric_with_stitching",
        "status": "in_progress",
        "rider_status": "measurement_taken",
        "tailor_status": "stitching_started",
        "payment_status": "paid",
        "payment_method": "credit_card",
        "subtotal": "500.00",
        "tax_amount": "75.00",
        "delivery_fee": "25.00",
        "total_amount": "600.00",
        "customer": {...},
        "tailor": {...},
        "rider": {...},
        "delivery_address": {...},
        "items": [...],
        "rider_measurements": {
            "chest": "40",
            "waist": "36",
            ...
        },
        "measurement_taken_at": "2024-12-18T11:30:00Z",
        "special_instructions": "Please make it extra comfortable",
        "appointment_date": "2024-12-20",
        "appointment_time": "14:00:00",
        "custom_styles": [...],
        "created_at": "2024-12-18T10:30:00Z",
        "updated_at": "2024-12-18T12:00:00Z"
    }
}
```

---

### Get Order Status History

**Endpoint:** `GET /api/orders/{order_id}/history/`

**Request:**
```bash
curl --location 'http://localhost:8000/api/orders/123/history/' \
--header 'Authorization: Bearer CUSTOMER_TOKEN'
```

**Response (200 OK):**
```json
{
    "success": true,
    "message": "Order history retrieved successfully",
    "data": [
        {
            "id": 1,
            "order": 123,
            "status": "confirmed",
            "previous_status": "pending",
            "changed_by": {
                "id": 2,
                "username": "tailor_user"
            },
            "notes": "Order accepted, will prepare fabric",
            "created_at": "2024-12-18T10:35:00Z"
        },
        {
            "id": 2,
            "order": 123,
            "status": "in_progress",
            "previous_status": "confirmed",
            "changed_by": {
                "id": 3,
                "username": "rider_user"
            },
            "notes": "Status: confirmed→in_progress, Rider: none→accepted, Tailor: none→accepted",
            "created_at": "2024-12-18T10:40:00Z"
        },
        {
            "id": 3,
            "order": 123,
            "status": "in_progress",
            "previous_status": "in_progress",
            "changed_by": {
                "id": 3,
                "username": "rider_user"
            },
            "notes": "Status: in_progress→in_progress, Rider: accepted→on_way_to_measurement, Tailor: accepted→accepted",
            "created_at": "2024-12-18T11:00:00Z"
        }
    ]
}
```

---

### Cancel Order (Customer Only)

**Endpoint:** `PATCH /api/orders/{order_id}/status/`

**Request:**
```bash
curl --location --request PATCH 'http://localhost:8000/api/orders/123/status/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer CUSTOMER_TOKEN' \
--data '{
    "status": "cancelled",
    "notes": "Customer cancelled the order"
}'
```

**Response (200 OK):**
```json
{
    "success": true,
    "message": "Order status updated successfully",
    "data": {
        "id": 123,
        "status": "cancelled",
        ...
    }
}
```

**What Happens:**
1. ✅ Order can only be cancelled when `status = 'pending'`
2. ✅ Only customer can cancel (tailor cannot)
3. ✅ **Notification Sent to Customer:**
   - Body: "Your order #ORD-A1B2C3D4 has been cancelled"

4. ✅ **Notification Sent to Tailor:**
   - Body: "Order #ORD-A1B2C3D4 has been cancelled by customer"

---

## Notification System

### Notification Types

#### 1. Order Status Notifications (`ORDER_STATUS`)

**Triggered When:**
- Order status changes via `OrderUpdateSerializer.update()`
- Rider status changes via `RiderUpdateOrderStatusView`
- Tailor status changes via order status update

**Notification Payload:**
```json
{
    "notification": {
        "title": "Order #ORD-A1B2C3D4 Update",
        "body": "Tailor has accepted your order #ORD-A1B2C3D4"
    },
    "data": {
        "type": "ORDER_STATUS",
        "category": "order_confirmed",
        "order_id": "123",
        "order_number": "ORD-A1B2C3D4",
        "status": "confirmed",
        "old_status": "pending"
    }
}
```

**Status Categories:**
- `order_pending` - Order created
- `order_confirmed` - Tailor accepted
- `order_in_progress` - Order being processed
- `order_ready_for_delivery` - Ready for pickup/delivery
- `order_delivered` - Order delivered
- `order_cancelled` - Order cancelled

---

#### 2. Payment Status Notifications (`PAYMENT`)

**Triggered When:**
- Payment status changes via `OrderPaymentStatusUpdateView`

**Notification Payload:**
```json
{
    "notification": {
        "title": "Payment Update",
        "body": "Payment of 600.00 received for order #ORD-A1B2C3D4"
    },
    "data": {
        "type": "PAYMENT",
        "category": "payment_paid",
        "order_id": "123",
        "order_number": "ORD-A1B2C3D4",
        "payment_status": "paid",
        "old_payment_status": "pending",
        "amount": "600.00"
    }
}
```

**Payment Categories:**
- `payment_paid` - Payment received
- `payment_pending` - Payment pending
- `payment_refunded` - Refund processed

---

#### 3. Rider Assignment Notifications (`RIDER_ASSIGNMENT`)

**Triggered When:**
- Rider accepts order via `RiderAcceptOrderView`

**Notification Payload:**
```json
{
    "notification": {
        "title": "Rider Assigned",
        "body": "Rider rider_user has been assigned to deliver your order #ORD-A1B2C3D4"
    },
    "data": {
        "type": "RIDER_ASSIGNMENT",
        "category": "rider_assigned",
        "order_id": "123",
        "order_number": "ORD-A1B2C3D4",
        "rider_id": "3",
        "rider_name": "rider_user"
    }
}
```

**Assignment Categories:**
- `rider_assigned` - Rider assigned (customer/tailor notification)
- `order_assigned` - Order assigned (rider notification)

---

### Notification Recipients

| Status Change | Customer | Tailor | Rider |
|---------------|----------|--------|-------|
| Order Created | ✅ | ✅ | ❌ |
| Order Confirmed | ✅ | ✅ | ❌ |
| Payment Paid | ✅ | ✅ | ❌ |
| Rider Assigned | ✅ | ✅ | ✅ |
| Rider Status Changed | ✅ | ✅ | ✅ |
| Tailor Status Changed | ✅ | ✅ | ❌ |
| Order Delivered | ✅ | ✅ | ✅ |
| Order Cancelled | ✅ | ✅ | ✅ (if assigned) |

---

### Get Notification Logs

**Endpoint:** `GET /api/notifications/logs/`

**Request:**
```bash
curl --location 'http://localhost:8000/api/notifications/logs/' \
--header 'Authorization: Bearer CUSTOMER_TOKEN'
```

**Response (200 OK):**
```json
{
    "success": true,
    "message": "Notification logs retrieved successfully",
    "data": [
        {
            "id": 1,
            "notification_type": "ORDER_STATUS",
            "category": "order_confirmed",
            "title": "Order #ORD-A1B2C3D4 Update",
            "body": "Tailor has accepted your order #ORD-A1B2C3D4",
            "status": "sent",
            "data": {
                "order_id": 123,
                "order_number": "ORD-A1B2C3D4",
                "status": "confirmed"
            },
            "sent_at": "2024-12-18T10:35:00Z",
            "created_at": "2024-12-18T10:35:00Z"
        },
        {
            "id": 2,
            "notification_type": "RIDER_ASSIGNMENT",
            "category": "rider_assigned",
            "title": "Rider Assigned",
            "body": "Rider rider_user has been assigned to deliver your order #ORD-A1B2C3D4",
            "status": "sent",
            "sent_at": "2024-12-18T10:40:00Z",
            "created_at": "2024-12-18T10:40:00Z"
        }
    ]
}
```

---

## Error Handling

### Invalid Status Transition

**Request:**
```bash
curl --location --request PATCH 'http://localhost:8000/api/orders/123/status/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer RIDER_TOKEN' \
--data '{
    "rider_status": "delivered"
}'
```

**Response (400 Bad Request):**
```json
{
    "success": false,
    "message": "Cannot change rider_status from accepted to delivered. Allowed: ['on_way_to_pickup']",
    "errors": {
        "status": "Cannot change rider_status from accepted to delivered. Allowed: ['on_way_to_pickup']"
    }
}
```

---

### Order Not Found

**Response (404 Not Found):**
```json
{
    "success": false,
    "message": "Order not found",
    "status_code": 404
}
```

---

### Unauthorized Access

**Response (403 Forbidden):**
```json
{
    "success": false,
    "message": "You can only update orders assigned to you",
    "status_code": 403
}
```

---

### Order Already Delivered

**Response (400 Bad Request):**
```json
{
    "success": false,
    "message": "Cannot change status of delivered order",
    "status_code": 400
}
```

---

### Rider Cannot Accept Pending Order

**Request:**
```bash
curl --location --request POST 'http://localhost:8000/api/riders/orders/123/accept/' \
--header 'Authorization: Bearer RIDER_TOKEN'
```

**Response (400 Bad Request):**
```json
{
    "success": false,
    "message": "Order is still pending tailor confirmation. Please wait for the tailor to accept the order.",
    "status_code": 400
}
```

---

## Complete Flow Diagrams

### Fabric Only Flow

```
┌─────────────┐
│   Customer  │
└──────┬──────┘
       │
       │ 1. Create Order (pending)
       ▼
┌─────────────────────────────────────┐
│ Order: pending                      │
│ rider_status: none                  │
│ tailor_status: none                 │
│ 🔔 Notify: Customer + Tailor        │
└──────┬──────────────────────────────┘
       │
       │ 2. Update Payment (paid)
       ▼
┌─────────────────────────────────────┐
│ Order: pending                      │
│ payment_status: paid                │
│ 🔔 Notify: Customer + Tailor        │
└──────┬──────────────────────────────┘
       │
       │ 3. Tailor Accepts (confirmed, accepted)
       ▼
┌─────────────────────────────────────┐
│ Order: confirmed                    │
│ tailor_status: accepted             │
│ 🔔 Notify: Customer + Tailor        │
└──────┬──────────────────────────────┘
       │
       │ 4. Tailor Marks In Progress
       ▼
┌─────────────────────────────────────┐
│ Order: in_progress                  │
│ 🔔 Notify: Customer + Tailor        │
└──────┬──────────────────────────────┘
       │
       │ 5. Tailor Marks Ready
       ▼
┌─────────────────────────────────────┐
│ Order: ready_for_delivery           │
│ 🔔 Notify: Customer + Tailor + Rider│
└──────┬──────────────────────────────┘
       │
       │ 6. Rider Accepts (accepted)
       ▼
┌─────────────────────────────────────┐
│ Order: confirmed                    │
│ rider_status: accepted              │
│ 🔔 Notify: Customer + Tailor + Rider│
└──────┬──────────────────────────────┘
       │
       │ 7. Rider On Way to Pickup
       ▼
┌─────────────────────────────────────┐
│ Order: in_progress                  │
│ rider_status: on_way_to_pickup     │
│ 🔔 Notify: All                     │
└──────┬──────────────────────────────┘
       │
       │ 8. Rider Picked Up
       ▼
┌─────────────────────────────────────┐
│ Order: ready_for_delivery           │
│ rider_status: picked_up             │
│ 🔔 Notify: All                     │
└──────┬──────────────────────────────┘
       │
       │ 9. Rider On Way to Delivery
       ▼
┌─────────────────────────────────────┐
│ Order: ready_for_delivery           │
│ rider_status: on_way_to_delivery   │
│ 🔔 Notify: All                     │
└──────┬──────────────────────────────┘
       │
       │ 10. Rider Delivered
       ▼
┌─────────────────────────────────────┐
│ Order: delivered                    │
│ rider_status: delivered             │
│ 🔔 Notify: Customer + Tailor + Rider│
└─────────────────────────────────────┘
```

---

### Fabric With Stitching Flow

```
┌─────────────┐
│   Customer  │
└──────┬──────┘
       │
       │ 1. Create Order (pending)
       ▼
┌─────────────────────────────────────┐
│ Order: pending                      │
│ 🔔 Notify: Customer + Tailor        │
└──────┬──────────────────────────────┘
       │
       │ 2. Payment Paid
       ▼
┌─────────────────────────────────────┐
│ payment_status: paid                │
│ 🔔 Notify: Customer + Tailor        │
└──────┬──────────────────────────────┘
       │
       │ 3. Tailor Accepts (confirmed, accepted)
       ▼
┌─────────────────────────────────────┐
│ Order: confirmed                    │
│ tailor_status: accepted             │
│ 🔔 Notify: Customer + Tailor        │
└──────┬──────────────────────────────┘
       │
       │ 4. Rider Accepts (accepted)
       ▼
┌─────────────────────────────────────┐
│ rider_status: accepted              │
│ 🔔 Notify: Customer + Tailor + Rider│
└──────┬──────────────────────────────┘
       │
       │ 5. Rider On Way to Measurement
       ▼
┌─────────────────────────────────────┐
│ Order: in_progress                  │
│ rider_status: on_way_to_measurement │
│ 🔔 Notify: Customer                 │
└──────┬──────────────────────────────┘
       │
       │ 6. Rider Takes Measurements
       ▼
┌─────────────────────────────────────┐
│ rider_status: measurement_taken     │
│ rider_measurements: {...}           │
│ 🔔 Notify: Customer + Tailor        │
└──────┬──────────────────────────────┘
       │
       │ 7. Tailor Starts Stitching
       ▼
┌─────────────────────────────────────┐
│ tailor_status: stitching_started   │
│ 🔔 Notify: Customer + Tailor        │
└──────┬──────────────────────────────┘
       │
       │ 8. Tailor Finishes Stitching
       ▼
┌─────────────────────────────────────┐
│ Order: ready_for_delivery           │
│ tailor_status: stitched             │
│ 🔔 Notify: Customer + Tailor + Rider│
└──────┬──────────────────────────────┘
       │
       │ 9. Rider On Way to Pickup
       ▼
┌─────────────────────────────────────┐
│ rider_status: on_way_to_pickup     │
│ 🔔 Notify: All                     │
└──────┬──────────────────────────────┘
       │
       │ 10. Rider Picked Up
       ▼
┌─────────────────────────────────────┐
│ rider_status: picked_up             │
│ 🔔 Notify: All                     │
└──────┬──────────────────────────────┘
       │
       │ 11. Rider On Way to Delivery
       ▼
┌─────────────────────────────────────┐
│ rider_status: on_way_to_delivery   │
│ 🔔 Notify: All                     │
└──────┬──────────────────────────────┘
       │
       │ 12. Rider Delivered
       ▼
┌─────────────────────────────────────┐
│ Order: delivered                    │
│ rider_status: delivered             │
│ 🔔 Notify: Customer + Tailor + Rider│
└─────────────────────────────────────┘
```

---

## Status Transition Rules

### Fabric Only

| Current Status | Current Rider Status | Next Rider Status | Next Main Status |
|----------------|---------------------|-------------------|------------------|
| confirmed | none | accepted | confirmed |
| confirmed | accepted | on_way_to_pickup | in_progress |
| in_progress | on_way_to_pickup | picked_up | ready_for_delivery |
| ready_for_delivery | picked_up | on_way_to_delivery | ready_for_delivery |
| ready_for_delivery | on_way_to_delivery | delivered | delivered |

### Fabric With Stitching

| Current Status | Current Rider Status | Current Tailor Status | Next Rider Status | Next Tailor Status | Next Main Status |
|----------------|---------------------|----------------------|-------------------|-------------------|------------------|
| confirmed | none | accepted | accepted | accepted | confirmed |
| confirmed | accepted | accepted | on_way_to_measurement | accepted | in_progress |
| in_progress | on_way_to_measurement | accepted | measurement_taken | accepted | in_progress |
| in_progress | measurement_taken | accepted | - | stitching_started | in_progress |
| in_progress | measurement_taken | stitching_started | - | stitched | in_progress |
| in_progress | measurement_taken | stitched | on_way_to_pickup | stitched | ready_for_delivery |
| ready_for_delivery | on_way_to_pickup | stitched | picked_up | stitched | ready_for_delivery |
| ready_for_delivery | picked_up | stitched | on_way_to_delivery | stitched | ready_for_delivery |
| ready_for_delivery | on_way_to_delivery | stitched | delivered | stitched | delivered |

---

## Key Points

### ✅ **Status Synchronization**
- Main `status` automatically syncs based on `rider_status` and `tailor_status`
- When `rider_status = 'delivered'`, main `status` becomes `delivered`
- When `tailor_status = 'stitched'` and rider picks up, main `status` becomes `ready_for_delivery`

### ✅ **Role Permissions**
- **Customer**: Can only cancel (`pending` → `cancelled`)
- **Tailor**: Can update `status` and `tailor_status` (cannot cancel)
- **Rider**: Can update `rider_status` only (cannot cancel)
- **Admin**: Can do everything

### ✅ **Validation**
- All transitions validated by `OrderStatusTransitionService`
- Invalid transitions return 400 error with clear message
- Sequential flow enforced (cannot skip steps)

### ✅ **Notifications**
- Sent automatically on every status change
- Recipients based on role and order state
- Logged in `NotificationLog` for tracking
- Uses Firebase Cloud Messaging (FCM)

### ✅ **History Tracking**
- Every status change recorded in `OrderStatusHistory`
- Includes previous status, new status, changed_by, and notes
- Complete audit trail for orders

---

This guide covers the complete order flow from creation to delivery with all API endpoints, notifications, and status transitions!










