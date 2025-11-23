# Order API Improvements Guide

## Summary of Changes

This document explains the improvements made to order APIs based on CTO-level recommendations and industry best practices.

---

## 1. Order Filtering Improvements

### ✅ **Tailor Orders - Separated Available vs My Orders**

#### **New Endpoint: Get Available Orders (Tailor)**
**Endpoint:** `GET /api/orders/tailor/available-orders/`

**Purpose:** Shows only orders that tailor can accept (pending, not yet accepted)

**Filter Logic:**
- `tailor = authenticated_user`
- `status = 'pending'`
- `tailor_status = 'none'`

**Request:**
```bash
curl --location 'http://localhost:8000/api/orders/tailor/available-orders/?payment_status=paid&order_type=fabric_only' \
--header 'Authorization: Bearer TAILOR_TOKEN'
```

**Response:**
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
            "rider_status": "none",
            "tailor_status": "none",
            "payment_status": "paid",
            "total_amount": "600.00",
            ...
        }
    ]
}
```

#### **Updated Endpoint: My Orders (Tailor)**
**Endpoint:** `GET /api/orders/tailor/my-orders/`

**Purpose:** Shows only orders that tailor has accepted (working on)

**Filter Logic:**
- `tailor = authenticated_user`
- `tailor_status IN ('accepted', 'stitching_started', 'stitched')`

**Request:**
```bash
curl --location 'http://localhost:8000/api/orders/tailor/my-orders/?status=in_progress' \
--header 'Authorization: Bearer TAILOR_TOKEN'
```

**Response:**
```json
{
    "success": true,
    "message": "Your tailor orders retrieved successfully",
    "data": [
        {
            "id": 123,
            "order_number": "ORD-A1B2C3D4",
            "status": "in_progress",
            "rider_status": "accepted",
            "tailor_status": "accepted",
            ...
        }
    ]
}
```

**Key Change:** Once tailor accepts an order, it moves from "available" to "my orders" and won't appear in available orders anymore.

---

### ✅ **Rider Orders - Separated Available vs My Orders**

#### **Updated Endpoint: Available Orders (Rider)**
**Endpoint:** `GET /api/riders/orders/available/`

**Filter Logic Updated:**
- `payment_status = 'paid'`
- `rider IS NULL` (not assigned)
- `rider_status = 'none'` (not accepted by any rider)
- `status IN ('confirmed', 'in_progress', 'ready_for_delivery')` (tailor must have accepted)

**Request:**
```bash
curl --location 'http://localhost:8000/api/riders/orders/available/?status=confirmed' \
--header 'Authorization: Bearer RIDER_TOKEN'
```

**Response:**
```json
{
    "success": true,
    "message": "Available orders retrieved successfully",
    "data": [
        {
            "id": 123,
            "order_number": "ORD-A1B2C3D4",
            "status": "confirmed",
            "rider_status": "none",
            "tailor_status": "accepted",
            ...
        }
    ]
}
```

#### **Updated Endpoint: My Orders (Rider)**
**Endpoint:** `GET /api/riders/orders/my-orders/`

**Filter Logic Updated:**
- `rider = authenticated_user`
- `rider_status IN ('accepted', 'on_way_to_pickup', 'picked_up', 'on_way_to_delivery', 'on_way_to_measurement', 'measurement_taken', 'delivered')`

**Request:**
```bash
curl --location 'http://localhost:8000/api/riders/orders/my-orders/?status=in_progress' \
--header 'Authorization: Bearer RIDER_TOKEN'
```

**Response:**
```json
{
    "success": true,
    "message": "Your orders retrieved successfully",
    "data": [
        {
            "id": 123,
            "order_number": "ORD-A1B2C3D4",
            "status": "in_progress",
            "rider_status": "on_way_to_pickup",
            "tailor_status": "accepted",
            ...
        }
    ]
}
```

**Key Change:** Once rider accepts an order, it moves from "available" to "my orders" and won't appear in available orders anymore.

---

## 2. Status Info in Order Responses

### ✅ **New Field: `status_info`**

All order detail APIs now include a `status_info` object with:
- Current statuses (status, rider_status, tailor_status)
- Next available actions (what user can do)
- Cancellation info
- Status progress

**Example Response:**
```json
{
    "success": true,
    "message": "Order retrieved successfully",
    "data": {
        "id": 123,
        "order_number": "ORD-A1B2C3D4",
        "order_type": "fabric_with_stitching",
        "status": "confirmed",
        "rider_status": "none",
        "tailor_status": "accepted",
        ...
        "status_info": {
            "current_status": "confirmed",
            "current_rider_status": "none",
            "current_tailor_status": "accepted",
            "next_available_actions": [
                {
                    "type": "status",
                    "value": "in_progress",
                    "label": "Mark In Progress",
                    "description": "Start processing this order",
                    "icon": "play-circle",
                    "role": "TAILOR",
                    "requires_confirmation": false,
                    "confirmation_message": null
                },
                {
                    "type": "rider_status",
                    "value": "accepted",
                    "label": "Accept Order",
                    "description": "Accept this order for delivery",
                    "icon": "check-circle",
                    "role": "RIDER",
                    "requires_confirmation": true,
                    "confirmation_message": "Are you sure you want to accept order?"
                }
            ],
            "can_cancel": false,
            "cancel_reason": "Orders can only be cancelled when status is pending",
            "status_progress": {
                "current_step": 2,
                "total_steps": 5,
                "percentage": 40
            }
        }
    }
}
```

---

## 3. Complete API Flow Examples

### **Tailor Flow**

#### Step 1: Get Available Orders (New Orders to Accept)
```bash
curl --location 'http://localhost:8000/api/orders/tailor/available-orders/' \
--header 'Authorization: Bearer TAILOR_TOKEN'
```

**Response:** Only shows orders with `status='pending'` and `tailor_status='none'`

#### Step 2: Accept Order
```bash
curl --location --request PATCH 'http://localhost:8000/api/orders/123/status/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer TAILOR_TOKEN' \
--data '{
    "status": "confirmed",
    "tailor_status": "accepted"
}'
```

**What Happens:**
- Order moves from "available-orders" to "my-orders"
- Order no longer appears in available-orders API
- Order appears in my-orders API

#### Step 3: Get My Orders (Accepted Orders)
```bash
curl --location 'http://localhost:8000/api/orders/tailor/my-orders/' \
--header 'Authorization: Bearer TAILOR_TOKEN'
```

**Response:** Only shows orders with `tailor_status IN ('accepted', 'stitching_started', 'stitched')`

---

### **Rider Flow**

#### Step 1: Get Available Orders (Orders to Accept)
```bash
curl --location 'http://localhost:8000/api/riders/orders/available/' \
--header 'Authorization: Bearer RIDER_TOKEN'
```

**Response:** Only shows orders with:
- `payment_status='paid'`
- `rider IS NULL`
- `rider_status='none'`
- `status IN ('confirmed', 'in_progress', 'ready_for_delivery')`

#### Step 2: Accept Order
```bash
curl --location --request POST 'http://localhost:8000/api/riders/orders/123/accept/' \
--header 'Authorization: Bearer RIDER_TOKEN'
```

**What Happens:**
- Order moves from "available" to "my-orders"
- Order no longer appears in available orders API
- Order appears in my-orders API

#### Step 3: Get My Orders (Accepted Orders)
```bash
curl --location 'http://localhost:8000/api/riders/orders/my-orders/' \
--header 'Authorization: Bearer RIDER_TOKEN'
```

**Response:** Only shows orders with `rider=user` and `rider_status != 'none'`

---

## 4. Status Info Field Details

### **Next Available Actions Structure**

Each action in `next_available_actions` contains:

```json
{
    "type": "rider_status",           // 'status', 'rider_status', or 'tailor_status'
    "value": "on_way_to_pickup",      // The status value to set
    "label": "Start Pickup",          // Human-readable label
    "description": "On way to pickup order from tailor",  // Description
    "icon": "car",                    // Icon name for UI
    "role": "RIDER",                  // Role that can perform this action
    "requires_confirmation": false,   // Whether to show confirmation dialog
    "confirmation_message": null      // Confirmation message if needed
}
```

### **Status Progress**

```json
{
    "current_step": 2,      // Current step number (1-5)
    "total_steps": 5,       // Total steps in order flow
    "percentage": 40        // Progress percentage (0-100)
}
```

**Progress Calculation:**
- `pending` = Step 1 (20%)
- `confirmed` = Step 2 (40%)
- `in_progress` = Step 3 (60%)
- `ready_for_delivery` = Step 4 (80%)
- `delivered` = Step 5 (100%)

---

## 5. Updated Serializers

### **OrderSerializer Changes**

**New Fields Added:**
- `rider_status` - Current rider activity status
- `tailor_status` - Current tailor activity status
- `status_info` - Complete status information with next actions

**Fields Included in status_info:**
- `current_status` - Main order status
- `current_rider_status` - Current rider status
- `current_tailor_status` - Current tailor status
- `next_available_actions` - Array of available actions
- `can_cancel` - Boolean indicating if order can be cancelled
- `cancel_reason` - Reason why order cannot be cancelled (if applicable)
- `status_progress` - Progress information

### **OrderListSerializer Changes**

**New Fields Added:**
- `order_type` - Type of order (fabric_only or fabric_with_stitching)
- `rider_status` - Current rider status
- `tailor_status` - Current tailor status

---

## 6. Benefits

### **For Frontend Developers:**

1. **No Need to Calculate Actions**
   - Backend provides `next_available_actions`
   - Frontend just displays the actions
   - No complex logic needed

2. **Clear Separation**
   - "Available orders" = Orders to accept
   - "My orders" = Orders being worked on
   - No confusion about which orders to show

3. **Better UX**
   - Show only valid actions
   - Prevent invalid API calls
   - Clear progress indicators

### **For Backend:**

1. **Single Source of Truth**
   - Status validation logic in one place
   - Consistent across all APIs
   - Easier to maintain

2. **Better Performance**
   - Filtered queries (less data)
   - Optimized database queries
   - Reduced API response size

---

## 7. Migration Notes

### **Breaking Changes:**

1. **Tailor Available Orders:**
   - Old: `GET /api/orders/tailor/my-orders/` showed all orders
   - New: `GET /api/orders/tailor/available-orders/` shows pending orders
   - New: `GET /api/orders/tailor/my-orders/` shows accepted orders only

2. **Rider Available Orders:**
   - Updated filter: Now excludes orders where `rider_status != 'none'`
   - Rider's accepted orders won't appear in available list

3. **Order Response:**
   - New fields: `rider_status`, `tailor_status`, `status_info`
   - All existing fields remain (backward compatible)

### **Non-Breaking Changes:**

- All existing endpoints still work
- New fields are additive (don't break existing code)
- Old fields still present for backward compatibility

---

## 8. Testing Examples

### **Test Tailor Flow:**

```bash
# 1. Get available orders (should show pending orders)
curl 'http://localhost:8000/api/orders/tailor/available-orders/' \
  -H 'Authorization: Bearer TAILOR_TOKEN'

# 2. Accept an order
curl -X PATCH 'http://localhost:8000/api/orders/123/status/' \
  -H 'Authorization: Bearer TAILOR_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{"status": "confirmed", "tailor_status": "accepted"}'

# 3. Check available orders again (should NOT show order 123)
curl 'http://localhost:8000/api/orders/tailor/available-orders/' \
  -H 'Authorization: Bearer TAILOR_TOKEN'

# 4. Check my orders (should show order 123)
curl 'http://localhost:8000/api/orders/tailor/my-orders/' \
  -H 'Authorization: Bearer TAILOR_TOKEN'
```

### **Test Rider Flow:**

```bash
# 1. Get available orders (should show orders without rider)
curl 'http://localhost:8000/api/riders/orders/available/' \
  -H 'Authorization: Bearer RIDER_TOKEN'

# 2. Accept an order
curl -X POST 'http://localhost:8000/api/riders/orders/123/accept/' \
  -H 'Authorization: Bearer RIDER_TOKEN'

# 3. Check available orders again (should NOT show order 123)
curl 'http://localhost:8000/api/riders/orders/available/' \
  -H 'Authorization: Bearer RIDER_TOKEN'

# 4. Check my orders (should show order 123)
curl 'http://localhost:8000/api/riders/orders/my-orders/' \
  -H 'Authorization: Bearer RIDER_TOKEN'
```

### **Test Status Info:**

```bash
# Get order details (should include status_info)
curl 'http://localhost:8000/api/orders/123/' \
  -H 'Authorization: Bearer TAILOR_TOKEN'
```

**Expected Response:**
```json
{
    "data": {
        "id": 123,
        "status": "confirmed",
        "rider_status": "none",
        "tailor_status": "accepted",
        "status_info": {
            "current_status": "confirmed",
            "next_available_actions": [
                {
                    "type": "status",
                    "value": "in_progress",
                    "label": "Mark In Progress",
                    ...
                }
            ],
            "can_cancel": false,
            "status_progress": {
                "current_step": 2,
                "total_steps": 5,
                "percentage": 40
            }
        }
    }
}
```

---

## 9. Frontend Usage Example

### **Flutter/Dart Example:**

```dart
// Get order with status info
final response = await apiService.getOrder(orderId);
final order = Order.fromJson(response['data']);
final statusInfo = response['data']['status_info'];

// Display available actions
for (final action in statusInfo['next_available_actions']) {
  if (action['role'] == currentUserRole) {
    showActionButton(
      label: action['label'],
      icon: action['icon'],
      onTap: () => updateOrderStatus(
        orderId: orderId,
        type: action['type'],
        value: action['value'],
      ),
      requiresConfirmation: action['requires_confirmation'],
    );
  }
}

// Show progress
final progress = statusInfo['status_progress'];
showProgressBar(
  current: progress['current_step'],
  total: progress['total_steps'],
  percentage: progress['percentage'],
);
```

---

## 10. API Endpoints Summary

### **Tailor Endpoints:**

| Endpoint | Purpose | Shows |
|----------|---------|-------|
| `GET /api/orders/tailor/available-orders/` | New orders to accept | `status='pending'`, `tailor_status='none'` |
| `GET /api/orders/tailor/my-orders/` | Accepted orders | `tailor_status IN ('accepted', 'stitching_started', 'stitched')` |
| `GET /api/orders/tailor/paid-orders/` | Paid orders | `payment_status='paid'` |
| `GET /api/orders/tailor/{id}/` | Order details | Full order with `status_info` |

### **Rider Endpoints:**

| Endpoint | Purpose | Shows |
|----------|---------|-------|
| `GET /api/riders/orders/available/` | Orders to accept | `rider IS NULL`, `rider_status='none'`, `status != 'pending'` |
| `GET /api/riders/orders/my-orders/` | Accepted orders | `rider=user`, `rider_status != 'none'` |
| `GET /api/riders/orders/{id}/` | Order details | Full order with `status_info` |

### **Customer Endpoints:**

| Endpoint | Purpose | Shows |
|----------|---------|-------|
| `GET /api/orders/customer/my-orders/` | Customer orders | All orders for customer |
| `GET /api/orders/{id}/` | Order details | Full order with `status_info` |

---

## 11. Key Improvements Summary

✅ **Separated Available vs My Orders**
- Tailor: Available orders (pending) vs My orders (accepted)
- Rider: Available orders (not accepted) vs My orders (accepted)

✅ **Status Info in Responses**
- Current statuses (status, rider_status, tailor_status)
- Next available actions with labels, icons, descriptions
- Cancellation info
- Progress tracking

✅ **Better Filtering**
- Accepted orders don't appear in available lists
- Clear separation of concerns
- Matches industry best practices

✅ **Frontend-Friendly**
- No need to calculate valid actions
- Clear action labels and icons
- Progress indicators included

---

This implementation follows industry best practices and significantly improves the developer and user experience!






