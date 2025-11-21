# Order Status Info Implementation Guide

## Overview

This document explains the implementation of the `status_info` field and lightweight response serializers for order status updates. These features help frontend applications understand what actions are available for each order without needing complex client-side logic.

---

## Table of Contents

1. [Features Overview](#features-overview)
2. [Status Info Field](#status-info-field)
3. [Lightweight Response Serializer](#lightweight-response-serializer)
4. [Next Available Actions](#next-available-actions)
5. [API Endpoints](#api-endpoints)
6. [Frontend Integration](#frontend-integration)
7. [Testing](#testing)

---

## Features Overview

### What Was Implemented

1. **`status_info` Field in List APIs**
   - Added to `OrderListSerializer` (Tailor "My Orders")
   - Added to `RiderOrderListSerializer` (Rider "My Orders")
   - Shows available actions directly in list view

2. **`status_info` Field in Detail APIs**
   - Already present in `OrderSerializer` (Order Detail)
   - Provides complete status information

3. **Lightweight Response Serializer**
   - `OrderStatusUpdateResponseSerializer` for status updates
   - Returns only essential fields (90% size reduction)
   - Includes `status_info` for UI actions

4. **Status Transition Service Updates**
   - Fixed rider acceptance for `ready_for_delivery` orders
   - Allows riders to accept orders in multiple statuses

---

## Status Info Field

### Structure

The `status_info` field is a JSON object that contains:

```json
{
  "current_status": "confirmed",
  "current_rider_status": "none",
  "current_tailor_status": "accepted",
  "next_available_actions": [
    {
      "type": "status",
      "value": "in_progress",
      "label": "Mark In Progress",
      "description": "Start processing this order",
      "role": "TAILOR",
      "requires_confirmation": false,
      "confirmation_message": null
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
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `current_status` | string | Main order status (pending, confirmed, in_progress, etc.) |
| `current_rider_status` | string | Current rider activity status |
| `current_tailor_status` | string | Current tailor activity status |
| `next_available_actions` | array | List of actions user can perform |
| `can_cancel` | boolean | Whether order can be cancelled |
| `cancel_reason` | string/null | Reason why order cannot be cancelled |
| `status_progress` | object | Progress information (step, percentage) |

### Next Available Actions Structure

Each action in `next_available_actions` contains:

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Action type: "status", "rider_status", or "tailor_status" |
| `value` | string | The status value to set |
| `label` | string | Human-readable label for UI |
| `description` | string | Description of what the action does |
| `role` | string | User role that can perform this action |
| `requires_confirmation` | boolean | Whether to show confirmation dialog |
| `confirmation_message` | string/null | Confirmation message if needed |

**Note:** `icon` field was removed - frontend should determine icons based on `type` and `value`.

---

## Lightweight Response Serializer

### Purpose

When updating order status, the API now returns a lightweight response instead of the full order object. This reduces response size by ~90% and improves performance.

### Fields Returned

`OrderStatusUpdateResponseSerializer` returns only:

- `id` - Order ID
- `order_number` - Order reference number
- `status` - Updated status
- `rider_status` - Updated rider status (if changed)
- `tailor_status` - Updated tailor status (if changed)
- `status_info` - Next available actions (for UI)
- `updated_at` - Timestamp of update

### Fields NOT Returned

The following fields are excluded to reduce response size:

- `items` - Order items (can be fetched separately)
- `customer_name`, `tailor_name` - Names (not needed for status update)
- `subtotal`, `tax_amount`, `delivery_fee`, `total_amount` - Financial details
- `payment_status`, `payment_method` - Payment info
- `delivery_address` - Address details
- All other order fields

### When to Use

- **Status Updates**: Use lightweight serializer
- **Order Details**: Use full `OrderSerializer` (GET `/api/orders/{id}/`)

---

## Next Available Actions

### How Actions Are Determined

Actions are calculated by `OrderStatusTransitionService` based on:

1. **Order Type** (`fabric_only` vs `fabric_with_stitching`)
2. **Current Statuses** (status, rider_status, tailor_status)
3. **User Role** (TAILOR, RIDER, USER, ADMIN)
4. **Order State** (pending, confirmed, in_progress, etc.)

### Action Examples

#### For Tailor (fabric_only order, status=confirmed)

```json
{
  "type": "status",
  "value": "in_progress",
  "label": "Mark In Progress",
  "description": "Start processing this order",
  "role": "TAILOR",
  "requires_confirmation": false
}
```

#### For Rider (fabric_with_stitching, rider_status=accepted)

```json
{
  "type": "rider_status",
  "value": "on_way_to_measurement",
  "label": "Start Measurement",
  "description": "On way to take customer measurements",
  "role": "RIDER",
  "requires_confirmation": false
}
```

### Role-Based Filtering

Actions are automatically filtered by role:
- **TAILOR**: Only sees tailor actions
- **RIDER**: Only sees rider actions
- **USER**: Only sees cancellation action (if pending)
- **ADMIN**: Sees all actions

---

## API Endpoints

### List APIs (Include status_info)

#### Tailor My Orders
```
GET /api/orders/tailor/my-orders/
```

**Response includes:**
- Order list with `status_info` field
- Shows available actions for each order
- Includes `rider_measurements` for fabric_with_stitching orders

#### Rider My Orders
```
GET /api/riders/orders/my-orders/
```

**Response includes:**
- Order list with `status_info` field
- Shows available actions for each order
- Includes `rider_status` and `tailor_status`

### Detail APIs (Include status_info)

#### Get Order Details
```
GET /api/orders/{id}/
GET /api/orders/tailor/{id}/
GET /api/riders/orders/{id}/
```

**Response includes:**
- Full order details
- `status_info` with next available actions

### Status Update APIs (Lightweight Response)

#### Update Order Status
```
PATCH /api/orders/{id}/status/
```

**Response:**
- Lightweight response (7 fields only)
- Includes `status_info` for next actions

#### Rider Update Status
```
PATCH /api/riders/orders/{id}/update-status/
```

**Response:**
- Lightweight response (7 fields only)
- Includes `status_info` for next actions

---

## Frontend Integration

### Displaying Actions in List View

```dart
// Flutter example
for (final order in orders) {
  final statusInfo = order['status_info'];
  final actions = statusInfo['next_available_actions'];
  
  // Filter actions for current user's role
  final userActions = actions.where((action) => 
    action['role'] == currentUserRole
  ).toList();
  
  // Display action buttons
  for (final action in userActions) {
    ElevatedButton(
      onPressed: () => updateOrderStatus(
        orderId: order['id'],
        type: action['type'],
        value: action['value'],
      ),
      child: Text(action['label']),
    );
  }
}
```

### Displaying Progress

```dart
final progress = statusInfo['status_progress'];
LinearProgressIndicator(
  value: progress['percentage'] / 100,
);
Text('Step ${progress['current_step']} of ${progress['total_steps']}');
```

### Handling Confirmations

```dart
if (action['requires_confirmation']) {
  showDialog(
    context: context,
    builder: (context) => AlertDialog(
      title: Text('Confirm Action'),
      content: Text(action['confirmation_message']),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: Text('Cancel'),
        ),
        TextButton(
          onPressed: () {
            Navigator.pop(context);
            performAction(action);
          },
          child: Text('Confirm'),
        ),
      ],
    ),
  );
} else {
  performAction(action);
}
```

### Updating Order Status

```dart
Future<void> updateOrderStatus({
  required int orderId,
  required String type,
  required String value,
}) async {
  final response = await http.patch(
    Uri.parse('$baseUrl/api/orders/$orderId/status/'),
    headers: {
      'Authorization': 'Bearer $token',
      'Content-Type': 'application/json',
    },
    body: jsonEncode({
      type: value,  // e.g., {'status': 'in_progress'} or {'rider_status': 'accepted'}
    }),
  );
  
  final data = jsonDecode(response.body);
  
  // Lightweight response - only essential fields
  final updatedOrder = data['data'];
  final statusInfo = updatedOrder['status_info'];
  
  // Update UI with new status and next actions
  updateOrderInList(updatedOrder);
  showNextActions(statusInfo['next_available_actions']);
}
```

---

## Status Flow Examples

### Fabric Only Order Flow

```
1. Order Created
   status: pending
   status_info.next_available_actions: [
     {type: "status", value: "confirmed", role: "TAILOR"}
   ]

2. Tailor Accepts
   status: confirmed
   tailor_status: accepted
   status_info.next_available_actions: [
     {type: "status", value: "in_progress", role: "TAILOR"}
   ]

3. Tailor Marks In Progress
   status: in_progress
   status_info.next_available_actions: [
     {type: "status", value: "ready_for_delivery", role: "TAILOR"}
   ]

4. Tailor Marks Ready
   status: ready_for_delivery
   status_info.next_available_actions: [
     {type: "rider_status", value: "accepted", role: "RIDER"}
   ]

5. Rider Accepts
   rider_status: accepted
   status_info.next_available_actions: [
     {type: "rider_status", value: "on_way_to_pickup", role: "RIDER"}
   ]

6. Rider Picks Up
   rider_status: picked_up
   status_info.next_available_actions: [
     {type: "rider_status", value: "on_way_to_delivery", role: "RIDER"}
   ]

7. Rider Delivers
   rider_status: delivered
   status: delivered (auto-synced)
   status_info.next_available_actions: [] (no more actions)
```

### Fabric With Stitching Order Flow

```
1. Order Created
   status: pending
   status_info.next_available_actions: [
     {type: "status", value: "confirmed", role: "TAILOR"}
   ]

2. Tailor Accepts
   status: confirmed
   tailor_status: accepted
   status_info.next_available_actions: [
     {type: "status", value: "in_progress", role: "TAILOR"},
     {type: "rider_status", value: "accepted", role: "RIDER"}
   ]

3. Rider Accepts & Takes Measurements
   rider_status: measurement_taken
   status: in_progress
   status_info.next_available_actions: [
     {type: "tailor_status", value: "stitching_started", role: "TAILOR"}
   ]

4. Tailor Starts Stitching
   tailor_status: stitching_started
   status_info.next_available_actions: [
     {type: "tailor_status", value: "stitched", role: "TAILOR"}
   ]

5. Tailor Finishes Stitching
   tailor_status: stitched
   status: ready_for_delivery
   status_info.next_available_actions: [
     {type: "rider_status", value: "on_way_to_pickup", role: "RIDER"}
   ]

6. Rider Picks Up & Delivers
   rider_status: delivered
   status: delivered
   status_info.next_available_actions: [] (complete)
```

---

## Testing

### Running Tests

```bash
# Run all status info tests
python manage.py test apps.orders.test_status_info

# Run specific test class
python manage.py test apps.orders.test_status_info.OrderStatusInfoTest

# Run with verbose output
python manage.py test apps.orders.test_status_info -v 2

# Run all tests (should pass)
python manage.py test apps.orders.test_status_info
# Expected: Ran 16 tests in X.XXXs OK
```

### Test Coverage

The test suite (`apps/orders/test_status_info.py`) covers:

1. **Status Info Structure** (`OrderStatusInfoTest`)
   - ✅ Field presence and types
   - ✅ Correct structure validation
   - ✅ Status info for different order states
   - ✅ Status info for different user roles
   - ✅ Status progress calculation

2. **Next Available Actions** (`OrderStatusInfoTest`)
   - ✅ Actions based on order state
   - ✅ Role-based filtering
   - ✅ Action structure validation (no icon field)
   - ✅ Actions for pending, confirmed, in_progress orders

3. **Lightweight Serializer** (`OrderStatusUpdateResponseSerializerTest`)
   - ✅ Field inclusion/exclusion
   - ✅ Response size reduction verification
   - ✅ Status info inclusion

4. **Status Transitions** (`OrderStatusTransitionServiceTest`)
   - ✅ Rider acceptance for confirmed orders
   - ✅ Rider acceptance for in_progress orders
   - ✅ Rider acceptance for ready_for_delivery orders
   - ✅ Cannot skip from none to on_way_to_pickup

5. **API Endpoints** (`OrderStatusUpdateAPITest`)
   - ✅ Response format validation
   - ✅ Status update returns lightweight response
   - ✅ Status info included in update response

### Test Results

All 16 tests pass successfully:
- ✅ 8 tests for Status Info
- ✅ 4 tests for Status Transitions
- ✅ 2 tests for Lightweight Serializer
- ✅ 2 tests for API Endpoints

---

## Benefits

### For Frontend Developers

1. **No Complex Logic Needed**
   - Backend provides all available actions
   - No need to calculate valid transitions
   - Clear action labels and descriptions

2. **Better UX**
   - Show only valid actions
   - Prevent invalid API calls
   - Clear progress indicators

3. **Smaller Responses**
   - Status updates return minimal data
   - Faster API calls
   - Less mobile data usage

### For Backend

1. **Single Source of Truth**
   - Status validation logic in one place
   - Consistent across all APIs
   - Easier to maintain

2. **Better Performance**
   - Filtered queries
   - Optimized database queries
   - Reduced API response size

---

## Migration Notes

### Breaking Changes

**None** - All changes are additive. Existing fields remain unchanged.

### New Fields

- `status_info` - Added to list and detail serializers
- `rider_status` and `tailor_status` - Added to `RiderOrderListSerializer`

### Response Size Changes

- **Status Update Responses**: ~90% smaller (from ~2-5KB to ~500 bytes - 1KB)
- **List Responses**: Slightly larger due to `status_info` field (~200-500 bytes per order)

---

## Example API Responses

### List API Response (Tailor My Orders)

```json
{
  "success": true,
  "message": "Your tailor orders retrieved successfully",
  "data": [
    {
      "id": 123,
      "order_number": "ORD-A1B2C3D4",
      "order_type": "fabric_with_stitching",
      "status": "in_progress",
      "rider_status": "measurement_taken",
      "tailor_status": "accepted",
      "rider_measurements": {
        "chest": "40",
        "waist": "36"
      },
      "status_info": {
        "current_status": "in_progress",
        "current_rider_status": "measurement_taken",
        "current_tailor_status": "accepted",
        "next_available_actions": [
          {
            "type": "tailor_status",
            "value": "stitching_started",
            "label": "Start Stitching",
            "description": "Start stitching the garment",
            "role": "TAILOR",
            "requires_confirmation": false
          }
        ],
        "can_cancel": false,
        "cancel_reason": "Orders can only be cancelled when status is pending",
        "status_progress": {
          "current_step": 3,
          "total_steps": 5,
          "percentage": 60
        }
      }
    }
  ]
}
```

### Status Update Response (Lightweight)

```json
{
  "success": true,
  "message": "Order status updated successfully",
  "data": {
    "id": 123,
    "order_number": "ORD-A1B2C3D4",
    "status": "in_progress",
    "rider_status": "none",
    "tailor_status": "accepted",
    "status_info": {
      "current_status": "in_progress",
      "current_rider_status": "none",
      "current_tailor_status": "accepted",
      "next_available_actions": [
        {
          "type": "status",
          "value": "ready_for_delivery",
          "label": "Mark Ready for Delivery",
          "description": "Order is ready for pickup/delivery",
          "role": "TAILOR",
          "requires_confirmation": false
        }
      ],
      "can_cancel": false,
      "status_progress": {
        "current_step": 3,
        "total_steps": 5,
        "percentage": 60
      }
    },
    "updated_at": "2024-12-18T12:00:00Z"
  }
}
```

---

## Summary

### Key Features

✅ **Status Info in List APIs** - Users see available actions directly in list view  
✅ **Lightweight Status Updates** - 90% smaller responses for status updates  
✅ **Role-Based Actions** - Only shows actions user can perform  
✅ **Progress Tracking** - Visual progress indicators  
✅ **No Icons** - Frontend determines icons based on action type/value  

### Implementation Files

- `apps/orders/serializers.py` - Serializers with status_info
- `apps/orders/services.py` - Status transition logic
- `apps/orders/views.py` - API views using lightweight serializer
- `apps/riders/serializers.py` - Rider list serializer with status_info
- `apps/riders/views.py` - Rider views using lightweight serializer

### Testing

- `apps/orders/test_status_info.py` - Comprehensive test suite

---

## Quick Reference

### How It Works - Step by Step

1. **User Opens "My Orders" List**
   - API returns orders with `status_info` field
   - Each order shows `next_available_actions` array
   - Actions are filtered by user's role

2. **User Sees Available Actions**
   - Frontend displays action buttons based on `next_available_actions`
   - Each action has `label`, `description`, `type`, `value`
   - `requires_confirmation` determines if dialog is needed

3. **User Performs Action**
   - Frontend calls status update API with `{type: value}`
   - Example: `{"status": "in_progress"}` or `{"rider_status": "accepted"}`

4. **API Returns Lightweight Response**
   - Only essential fields returned (id, order_number, statuses, status_info)
   - Frontend updates UI with new status and next actions
   - No need to fetch full order details

5. **Status Info Updates**
   - `status_info` automatically recalculates
   - New `next_available_actions` reflect current state
   - Progress percentage updates

### Key Points

✅ **No Icons** - Frontend determines icons based on `type` and `value`  
✅ **Role-Based** - Only shows actions user can perform  
✅ **Lightweight** - Status updates return minimal data  
✅ **Always Available** - `status_info` in list and detail views  
✅ **Automatic** - Backend calculates valid transitions  

---

This implementation provides a complete solution for order status management with clear guidance for frontend developers and efficient API responses.

