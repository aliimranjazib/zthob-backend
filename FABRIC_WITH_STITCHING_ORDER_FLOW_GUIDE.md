# Fabric With Stitching Order Flow - Complete API Guide

## Overview

This guide documents the complete API flow for `fabric_with_stitching` orders from customer creation to final delivery. 

**Order Type:** `fabric_with_stitching`  
**Status Flow:** `pending` → `confirmed` → `in_progress` → `ready_for_delivery` → `delivered`

**Key Difference from Fabric Only:** This flow includes measurement taking by rider and stitching by tailor before delivery.

---

## Prerequisites

### 1. Register FCM Tokens (Required for Notifications)

Same as fabric_only - all users must register their FCM tokens.

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
    "order_type": "fabric_with_stitching",
    "payment_method": "credit_card",
    "delivery_address": 1,
    "items": [
        {
            "fabric": 5,
            "quantity": 2,
            "measurements": {
                "chest": "40",
                "waist": "36"
            }
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
        "items": [
            {
                "id": 1,
                "fabric": {
                    "id": 5,
                    "name": "Premium Cotton",
                    "price": "250.00"
                },
                "quantity": 2,
                "measurements": {
                    "chest": "40",
                    "waist": "36"
                }
            }
        ],
        "custom_styles": [...],
        "created_at": "2024-12-18T10:30:00Z"
    }
}
```

**What Happens:**
1. ✅ Order created with `status: "pending"`
2. ✅ `rider_status: "none"` (no rider assigned yet)
3. ✅ `tailor_status: "none"` (tailor hasn't accepted yet)
4. ✅ `payment_status: "pending"` (payment not completed)
5. ✅ Fabric stock is reduced by quantity
6. ✅ **Notification Sent to Tailor:** "New order #ORD-A1B2C3D4 received"
7. ✅ **Notification Sent to Customer:** "Your order #ORD-A1B2C3D4 has been placed successfully"

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
2. ✅ **Notification Sent to Tailor:** "Order #ORD-A1B2C3D4 payment received"
3. ✅ **Notification Sent to Customer:** "Payment for order #ORD-A1B2C3D4 confirmed"

**Note:** Payment must be `paid` before tailor can accept and rider can accept.

---

### Step 3: Tailor Views Available Orders

**Endpoint:** `GET /api/orders/tailor/available-orders/`

**Request:**
```bash
curl --location 'http://localhost:8000/api/orders/tailor/available-orders/?order_type=fabric_with_stitching&payment_status=paid' \
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
            "order_type": "fabric_with_stitching",
            "status": "pending",
            "tailor_status": "none",
            "payment_status": "paid",
            "total_amount": "600.00",
            "customer": {...},
            "items": [...]
        }
    ]
}
```

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
    "notes": "Order accepted, waiting for measurements"
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
            "next_available_actions": [
                {
                    "type": "status",
                    "value": "in_progress",
                    "label": "Mark In Progress",
                    "role": "TAILOR"
                }
            ]
        },
        "updated_at": "2024-12-18T11:00:00Z"
    }
}
```

**What Happens:**
1. ✅ `status` changed: `pending` → `confirmed`
2. ✅ `tailor_status` changed: `none` → `accepted`
3. ✅ **Notification Sent to Customer:** "Tailor has accepted your order #ORD-A1B2C3D4"

**Important:** Once `status: "confirmed"`, order can no longer be cancelled by customer.

---

### Step 5: Rider Views Available Orders

**Endpoint:** `GET /api/riders/orders/available/`

**Request:**
```bash
curl --location 'http://localhost:8000/api/riders/orders/available/?order_type=fabric_with_stitching' \
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
            "order_type": "fabric_with_stitching",
            "status": "confirmed",
            "rider_status": "none",
            "payment_status": "paid",
            "delivery_address": {...},
            "pickup_address": {...}
        }
    ]
}
```

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
4. ✅ **Notification Sent to Customer:** "Rider assigned to your order #ORD-A1B2C3D4"
5. ✅ **Notification Sent to Tailor:** "Rider assigned to order #ORD-A1B2C3D4"
6. ✅ **Notification Sent to Rider:** "Order #ORD-A1B2C3D4 accepted successfully"

**Requirements:**
- Order `payment_status` must be `paid`
- Order `status` must NOT be `pending` (must be `confirmed` or beyond)
- Rider must be approved
- Order must not already have a rider assigned

---

### Step 7: Rider Updates Status - On Way to Measurement

**Endpoint:** `PATCH /api/riders/orders/{order_id}/update-status/`

**Request:**
```bash
curl --location --request PATCH 'http://localhost:8000/api/riders/orders/123/update-status/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer RIDER_TOKEN' \
--data '{
    "rider_status": "on_way_to_measurement",
    "notes": "On my way to take customer measurements"
}'
```

**Response (200 OK):**
```json
{
    "success": true,
    "message": "Order rider status updated to On Way to Measurement",
    "data": {
        "id": 123,
        "order_number": "ORD-A1B2C3D4",
        "status": "in_progress",
        "rider_status": "on_way_to_measurement",
        "tailor_status": "accepted",
        "status_info": {
            "current_status": "in_progress",
            "current_rider_status": "on_way_to_measurement",
            "next_available_actions": [
                {
                    "type": "rider_status",
                    "value": "measurement_taken",
                    "label": "Mark Measurement Taken",
                    "description": "After taking measurements at customer location",
                    "role": "RIDER"
                }
            ]
        },
        "updated_at": "2024-12-18T11:15:00Z"
    }
}
```

**What Happens:**
1. ✅ `rider_status` changed: `accepted` → `on_way_to_measurement`
2. ✅ Main `status` auto-synced: `confirmed` → `in_progress`
3. ✅ **Notification Sent to Customer:** "Rider is on the way to take your measurements for order #ORD-A1B2C3D4"
4. ✅ **Notification Sent to Tailor:** "Rider is on the way to take measurements for order #ORD-A1B2C3D4"

**Note:** This step is unique to `fabric_with_stitching` orders. Rider must go to customer location to take measurements.

---

### Step 8: Rider Takes Measurements

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
    "notes": "Measurements taken successfully. Customer prefers loose fit."
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
        "status_info": {
            "current_status": "in_progress",
            "current_rider_status": "measurement_taken",
            "current_tailor_status": "accepted",
            "next_available_actions": [
                {
                    "type": "tailor_status",
                    "value": "stitching_started",
                    "label": "Start Stitching",
                    "description": "Begin stitching the garment",
                    "role": "TAILOR"
                }
            ]
        },
        ...
    }
}
```

**What Happens:**
1. ✅ `rider_status` changed: `on_way_to_measurement` → `measurement_taken`
2. ✅ Measurements stored in `rider_measurements` field (JSON)
3. ✅ `measurement_taken_at` timestamp set
4. ✅ Rider assignment status updated to `in_progress`
5. ✅ **Notification Sent to Customer:** "Measurements taken for order #ORD-A1B2C3D4"
6. ✅ **Notification Sent to Tailor:** "Measurements ready for order #ORD-A1B2C3D4 - you can start stitching"

**Important:** 
- This endpoint is **ONLY** for `fabric_with_stitching` orders
- Measurements are stored as JSON object
- After measurements are taken, tailor can start stitching

---

### Step 9: Tailor Views Order with Measurements

**Endpoint:** `GET /api/orders/tailor/{order_id}/`

**Request:**
```bash
curl --location 'http://localhost:8000/api/orders/tailor/123/' \
--header 'Authorization: Bearer TAILOR_TOKEN'
```

**Response (200 OK):**
```json
{
    "success": true,
    "message": "Order details retrieved successfully",
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
        "items": [...],
        "custom_styles": [...],
        ...
    }
}
```

**What Happens:**
- Tailor can now see the measurements taken by rider
- Tailor can view custom styles selected by customer
- Tailor can proceed with stitching

---

### Step 10: Tailor Starts Stitching

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
        "order_number": "ORD-A1B2C3D4",
        "status": "in_progress",
        "rider_status": "measurement_taken",
        "tailor_status": "stitching_started",
        "status_info": {
            "current_status": "in_progress",
            "current_rider_status": "measurement_taken",
            "current_tailor_status": "stitching_started",
            "next_available_actions": [
                {
                    "type": "tailor_status",
                    "value": "stitched",
                    "label": "Mark Stitched",
                    "description": "Stitching completed",
                    "role": "TAILOR"
                }
            ]
        },
        "updated_at": "2024-12-18T12:00:00Z"
    }
}
```

**What Happens:**
1. ✅ `tailor_status` changed: `accepted` → `stitching_started`
2. ✅ **Notification Sent to Customer:** "Your garment is being stitched for order #ORD-A1B2C3D4"
3. ✅ **Notification Sent to Rider:** "Order #ORD-A1B2C3D4 is being stitched"

**Note:** Tailor can only start stitching when `rider_status: "measurement_taken"` and `tailor_status: "accepted"`.

---

### Step 11: Tailor Finishes Stitching

**Endpoint:** `PATCH /api/orders/{order_id}/status/`

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

**Response (200 OK):**
```json
{
    "success": true,
    "message": "Order status updated successfully",
    "data": {
        "id": 123,
        "order_number": "ORD-A1B2C3D4",
        "status": "ready_for_delivery",
        "rider_status": "measurement_taken",
        "tailor_status": "stitched",
        "status_info": {
            "current_status": "ready_for_delivery",
            "current_rider_status": "measurement_taken",
            "current_tailor_status": "stitched",
            "next_available_actions": [
                {
                    "type": "rider_status",
                    "value": "on_way_to_pickup",
                    "label": "On Way to Pickup",
                    "description": "Rider can now pickup the stitched garment",
                    "role": "RIDER"
                }
            ]
        },
        "updated_at": "2024-12-18T14:00:00Z"
    }
}
```

**What Happens:**
1. ✅ `tailor_status` changed: `stitching_started` → `stitched`
2. ✅ Main `status` changed: `in_progress` → `ready_for_delivery`
3. ✅ **Notification Sent to Customer:** "Your order #ORD-A1B2C3D4 is ready for delivery"
4. ✅ **Notification Sent to Tailor:** "Order #ORD-A1B2C3D4 is ready for pickup"
5. ✅ **Notification Sent to Rider:** "Order #ORD-A1B2C3D4 is ready for pickup from tailor"

**Important:** Rider can only proceed to `on_way_to_pickup` when `tailor_status: "stitched"`.

---

### Step 12: Rider Updates Status - On Way to Pickup

**Endpoint:** `PATCH /api/riders/orders/{order_id}/update-status/`

**Request:**
```bash
curl --location --request PATCH 'http://localhost:8000/api/riders/orders/123/update-status/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer RIDER_TOKEN' \
--data '{
    "rider_status": "on_way_to_pickup",
    "notes": "On my way to pickup stitched garment from tailor"
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
        "status": "ready_for_delivery",
        "rider_status": "on_way_to_pickup",
        "tailor_status": "stitched",
        "status_info": {
            "next_available_actions": [
                {
                    "type": "rider_status",
                    "value": "picked_up",
                    "label": "Mark Picked Up",
                    "role": "RIDER"
                }
            ]
        },
        "updated_at": "2024-12-18T14:15:00Z"
    }
}
```

**What Happens:**
1. ✅ `rider_status` changed: `measurement_taken` → `on_way_to_pickup`
2. ✅ Main `status` remains: `ready_for_delivery`
3. ✅ **Notification Sent to Customer:** "Rider is on the way to pickup your order #ORD-A1B2C3D4"
4. ✅ **Notification Sent to Tailor:** "Rider is on the way to pickup order #ORD-A1B2C3D4"

**Note:** Rider can only proceed to `on_way_to_pickup` when `tailor_status: "stitched"`.

---

### Step 13: Rider Updates Status - Picked Up

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
        "status_info": {
            "next_available_actions": [
                {
                    "type": "rider_status",
                    "value": "on_way_to_delivery",
                    "label": "On Way to Delivery",
                    "role": "RIDER"
                }
            ]
        },
        "updated_at": "2024-12-18T14:30:00Z"
    }
}
```

**What Happens:**
1. ✅ `rider_status` changed: `on_way_to_pickup` → `picked_up`
2. ✅ Main `status` remains: `ready_for_delivery`
3. ✅ **Notification Sent to Customer:** "Your order #ORD-A1B2C3D4 has been picked up and is ready for delivery"
4. ✅ **Notification Sent to Tailor:** "Order #ORD-A1B2C3D4 has been picked up by rider"

---

### Step 14: Rider Updates Status - On Way to Delivery

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
        "status_info": {
            "next_available_actions": [
                {
                    "type": "rider_status",
                    "value": "delivered",
                    "label": "Mark Delivered",
                    "role": "RIDER"
                }
            ]
        },
        "updated_at": "2024-12-18T14:45:00Z"
    }
}
```

**What Happens:**
1. ✅ `rider_status` changed: `picked_up` → `on_way_to_delivery`
2. ✅ Main `status` remains: `ready_for_delivery`
3. ✅ **Notification Sent to Customer:** "Rider is on the way to deliver your order #ORD-A1B2C3D4"
4. ✅ **Notification Sent to Tailor:** "Order #ORD-A1B2C3D4 is on the way to customer"

---

### Step 15: Rider Updates Status - Delivered (FINAL STEP)

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
        "tailor_status": "stitched",
        "actual_delivery_date": "2024-12-18",
        "status_info": {
            "current_status": "delivered",
            "current_rider_status": "delivered",
            "current_tailor_status": "stitched",
            "next_available_actions": []
        },
        "updated_at": "2024-12-18T15:00:00Z"
    }
}
```

**What Happens:**
1. ✅ `rider_status` changed: `on_way_to_delivery` → `delivered`
2. ✅ Main `status` changed: `ready_for_delivery` → `delivered` (automatic)
3. ✅ `actual_delivery_date` set to today
4. ✅ `RiderOrderAssignment` marked as `completed`
5. ✅ Rider statistics updated (`total_deliveries += 1`)
6. ✅ **Notification Sent to Customer:** "Your order #ORD-A1B2C3D4 has been delivered"
7. ✅ **Notification Sent to Tailor:** "Order #ORD-A1B2C3D4 has been delivered to customer"
8. ✅ **Notification Sent to Rider:** "Order #ORD-A1B2C3D4 delivery completed"

**Order Status:** `delivered` (FINAL STATE - no further changes allowed)

---

## Complete Status Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│              FABRIC_WITH_STITCHING ORDER FLOW                   │
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
Step 5: Rider On Way to Measurement
┌─────────────────────────────────────┐
│ Order: in_progress                  │
│ rider_status: on_way_to_measurement │
│ 🔔 Notify: Customer + Tailor        │
└─────────────────────────────────────┘
              ↓
Step 6: Rider Takes Measurements
┌─────────────────────────────────────┐
│ Order: in_progress                  │
│ rider_status: measurement_taken     │
│ rider_measurements: {...}           │
│ measurement_taken_at: [timestamp]   │
│ 🔔 Notify: Customer + Tailor        │
└─────────────────────────────────────┘
              ↓
Step 7: Tailor Starts Stitching
┌─────────────────────────────────────┐
│ Order: in_progress                  │
│ tailor_status: stitching_started    │
│ 🔔 Notify: Customer + Rider          │
└─────────────────────────────────────┘
              ↓
Step 8: Tailor Finishes Stitching
┌─────────────────────────────────────┐
│ Order: ready_for_delivery           │
│ tailor_status: stitched             │
│ 🔔 Notify: Customer + Tailor + Rider│
└─────────────────────────────────────┘
              ↓
Step 9: Rider On Way to Pickup
┌─────────────────────────────────────┐
│ Order: ready_for_delivery           │
│ rider_status: on_way_to_pickup     │
│ 🔔 Notify: Customer + Tailor        │
└─────────────────────────────────────┘
              ↓
Step 10: Rider Picked Up
┌─────────────────────────────────────┐
│ Order: ready_for_delivery           │
│ rider_status: picked_up              │
│ 🔔 Notify: Customer + Tailor        │
└─────────────────────────────────────┘
              ↓
Step 11: Rider On Way to Delivery
┌─────────────────────────────────────┐
│ Order: ready_for_delivery           │
│ rider_status: on_way_to_delivery    │
│ 🔔 Notify: Customer + Tailor        │
└─────────────────────────────────────┘
              ↓
Step 12: Rider Delivered (FINAL)
┌─────────────────────────────────────┐
│ Order: delivered                    │
│ rider_status: delivered              │
│ actual_delivery_date: [today]       │
│ 🔔 Notify: Customer + Tailor + Rider│
└─────────────────────────────────────┘
```

---

## Status Transition Rules

### Allowed Transitions for Fabric With Stitching Orders

| Current Status | Current Rider Status | Current Tailor Status | Next Rider Status | Next Tailor Status | Next Main Status | Who Can Update |
|----------------|---------------------|----------------------|-------------------|-------------------|------------------|----------------|
| `pending` | `none` | `none` | - | `accepted` | `confirmed` | TAILOR |
| `pending` | `none` | `none` | - | - | `cancelled` | USER (customer) |
| `confirmed` | `none` | `accepted` | `accepted` | - | `confirmed` | RIDER |
| `confirmed` | `accepted` | `accepted` | `on_way_to_measurement` | - | `in_progress` | RIDER |
| `in_progress` | `on_way_to_measurement` | `accepted` | `measurement_taken` | - | `in_progress` | RIDER |
| `in_progress` | `measurement_taken` | `accepted` | - | `stitching_started` | `in_progress` | TAILOR |
| `in_progress` | `measurement_taken` | `stitching_started` | - | `stitched` | `in_progress` | TAILOR |
| `in_progress` | `measurement_taken` | `stitched` | `on_way_to_pickup` | - | `ready_for_delivery` | RIDER |
| `ready_for_delivery` | `on_way_to_pickup` | `stitched` | `picked_up` | - | `ready_for_delivery` | RIDER |
| `ready_for_delivery` | `picked_up` | `stitched` | `on_way_to_delivery` | - | `ready_for_delivery` | RIDER |
| `ready_for_delivery` | `on_way_to_delivery` | `stitched` | `delivered` | - | `delivered` | RIDER |

### Key Differences from Fabric Only

1. **Measurement Step:** Rider must take measurements before tailor can stitch
2. **Stitching Steps:** Tailor must start and finish stitching before rider can pickup
3. **Sequential Dependencies:**
   - Rider cannot proceed to `on_way_to_pickup` until `tailor_status: "stitched"`
   - Tailor cannot start stitching until `rider_status: "measurement_taken"`
   - Tailor must complete stitching (`stitched`) before rider can pickup

---

## Key API Endpoints Summary

### Customer Endpoints
- `POST /api/orders/create/` - Create order (with `order_type: "fabric_with_stitching"`)
- `PATCH /api/orders/{order_id}/payment-status/` - Update payment status
- `GET /api/orders/customer/my-orders/` - View my orders
- `GET /api/orders/{order_id}/` - View order details (includes `rider_measurements`)

### Tailor Endpoints
- `GET /api/orders/tailor/available-orders/` - View pending orders
- `GET /api/orders/tailor/my-orders/` - View accepted orders (includes `rider_measurements`)
- `GET /api/orders/tailor/{order_id}/` - View order details (includes `rider_measurements`)
- `PATCH /api/orders/{order_id}/status/` - Update order status (accept, start stitching, finish stitching)

### Rider Endpoints
- `GET /api/riders/orders/available/` - View available orders
- `GET /api/riders/orders/my-orders/` - View my assigned orders
- `GET /api/riders/orders/{order_id}/` - View order details
- `POST /api/riders/orders/{order_id}/accept/` - Accept order
- `PATCH /api/riders/orders/{order_id}/update-status/` - Update rider status
- `POST /api/riders/orders/{order_id}/measurements/` - Add measurements (fabric_with_stitching only)

---

## Important Notes

1. **Measurement Endpoint:** `POST /api/riders/orders/{order_id}/measurements/` is **ONLY** for `fabric_with_stitching` orders.

2. **Sequential Dependencies:**
   - Rider must take measurements before tailor can start stitching
   - Tailor must finish stitching before rider can pickup
   - These dependencies are enforced by the transition service

3. **Measurements Storage:**
   - Measurements are stored in `rider_measurements` field (JSON)
   - `measurement_taken_at` timestamp is automatically set
   - Tailor can view measurements via tailor order detail endpoint

4. **Status Auto-Sync:** The main `status` automatically syncs based on `rider_status` and `tailor_status`:
   - When `rider_status: "on_way_to_measurement"` → `status: "in_progress"`
   - When `tailor_status: "stitched"` and `rider_status: "on_way_to_pickup"` → `status: "ready_for_delivery"`
   - When `rider_status: "delivered"` → `status: "delivered"`

5. **Custom Styles:** For `fabric_with_stitching` orders, customers can select custom styles (collar, sleeves, etc.) which are visible to tailor.

6. **Appointment Fields:** Customers can optionally set `appointment_date` and `appointment_time` for measurement taking.

---

## Testing the Flow

### Quick Test Sequence

1. **Create Order:**
   ```bash
   POST /api/orders/create/
   # order_type: "fabric_with_stitching"
   # Save order_id
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

5. **Rider On Way to Measurement:**
   ```bash
   PATCH /api/riders/orders/{order_id}/update-status/
   # rider_status: "on_way_to_measurement"
   ```

6. **Rider Takes Measurements:**
   ```bash
   POST /api/riders/orders/{order_id}/measurements/
   # measurements: {...}
   ```

7. **Tailor Starts Stitching:**
   ```bash
   PATCH /api/orders/{order_id}/status/
   # tailor_status: "stitching_started"
   ```

8. **Tailor Finishes Stitching:**
   ```bash
   PATCH /api/orders/{order_id}/status/
   # tailor_status: "stitched", status: "ready_for_delivery"
   ```

9. **Rider Updates Status:**
   ```bash
   PATCH /api/riders/orders/{order_id}/update-status/
   # rider_status: "on_way_to_pickup"
   # rider_status: "picked_up"
   # rider_status: "on_way_to_delivery"
   # rider_status: "delivered"
   ```

---

## Comparison: Fabric Only vs Fabric With Stitching

| Feature | Fabric Only | Fabric With Stitching |
|---------|-------------|----------------------|
| **Measurement Step** | ❌ No | ✅ Yes (rider takes measurements) |
| **Stitching Steps** | ❌ No | ✅ Yes (tailor stitches) |
| **Rider Flow** | `accepted` → `on_way_to_pickup` → `picked_up` → `on_way_to_delivery` → `delivered` | `accepted` → `on_way_to_measurement` → `measurement_taken` → `on_way_to_pickup` → `picked_up` → `on_way_to_delivery` → `delivered` |
| **Tailor Flow** | `accepted` → (optional: `in_progress`) | `accepted` → `stitching_started` → `stitched` |
| **Dependencies** | None | Rider must take measurements before tailor can stitch |
| **Special Endpoint** | None | `POST /api/riders/orders/{order_id}/measurements/` |

---

**Last Updated:** 2024-12-18  
**Version:** 1.0

