# Delivery Tracking Feature Documentation

## Overview

The delivery tracking feature provides real-time location tracking for order deliveries. It allows:
- **Riders** to update their location during delivery
- **Customers** to track their orders in real-time
- **Admins/Tailors** to monitor delivery progress on the dashboard

## Features

- ✅ Real-time location updates (polling every 15 seconds)
- ✅ Location history tracking (30-day retention)
- ✅ ETA (Estimated Time of Arrival) calculation
- ✅ Distance tracking (total and estimated)
- ✅ Route visualization data
- ✅ Automatic tracking creation when rider is assigned
- ✅ Admin dashboard support

## Database Models

### DeliveryTracking
Main model for tracking delivery progress:
- Order and rider information
- Pickup and delivery locations
- Current status and timestamps
- Distance and ETA calculations
- Last known location

### LocationHistory
Stores historical location updates:
- GPS coordinates with timestamps
- Speed, heading, accuracy (if available)
- Distance from previous location
- Automatically cleaned up after 30 days

## API Endpoints

### Rider Endpoints

#### 1. Update Location
**POST** `/api/deliveries/rider/orders/<order_id>/update-location/`

Update rider's current location. Should be called every 15 seconds during active delivery.

**Request Body:**
```json
{
  "latitude": 24.7136,
  "longitude": 46.6753,
  "accuracy": 10.5,
  "speed": 45.0,
  "heading": 180.0,
  "status": "on_way_to_delivery"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Location updated successfully",
  "data": {
    "tracking": { ... },
    "distance_from_previous_km": 0.5
  }
}
```

#### 2. Get Tracking (Rider)
**GET** `/api/deliveries/rider/orders/<order_id>/tracking/`

Get detailed tracking information for rider's assigned order.

### Customer Endpoints

#### 1. Get Tracking (Customer)
**GET** `/api/deliveries/customer/orders/<order_id>/tracking/`

Get real-time tracking information for customer's order.

**Response:**
```json
{
  "success": true,
  "message": "Tracking information retrieved successfully",
  "data": {
    "id": 1,
    "order_number": "ORD-ABC123",
    "rider_name": "John Doe",
    "current_status": "on_way_to_delivery",
    "current_location": {
      "latitude": 24.7136,
      "longitude": 46.6753,
      "updated_at": "2025-01-15T10:30:00Z"
    },
    "delivery_address": "123 Main St, Riyadh",
    "estimated_distance_km": 2.5,
    "estimated_time_minutes": 5,
    "estimated_arrival_time": "2025-01-15T10:35:00Z",
    "total_distance_km": 15.3,
    "picked_up_at": "2025-01-15T10:20:00Z",
    "delivery_started_at": "2025-01-15T10:25:00Z",
    "recent_route": [
      {
        "latitude": 24.7100,
        "longitude": 46.6700,
        "timestamp": "2025-01-15T10:25:00Z"
      },
      ...
    ],
    "last_location_update": "2025-01-15T10:30:00Z"
  }
}
```

#### 2. Get Location History
**GET** `/api/deliveries/customer/orders/<order_id>/tracking/history/?limit=50`

Get location history for customer's order.

**Query Parameters:**
- `limit`: Number of location points to return (default: 50)

### Admin/Tailor Endpoints

#### 1. Get Tracking (Admin/Tailor)
**GET** `/api/deliveries/admin/orders/<order_id>/tracking/`

Get detailed tracking information with full location history.

#### 2. Get Route Data
**GET** `/api/deliveries/admin/orders/<order_id>/tracking/route/`

Get route visualization data for admin dashboard. Returns all location points for mapping.

**Response:**
```json
{
  "success": true,
  "message": "Route data retrieved successfully",
  "data": {
    "order_id": 123,
    "order_number": "ORD-ABC123",
    "pickup_location": {
      "latitude": 24.7000,
      "longitude": 46.6500,
      "address": "Tailor Shop Address"
    },
    "delivery_location": {
      "latitude": 24.7136,
      "longitude": 46.6753,
      "address": "Customer Address"
    },
    "current_location": {
      "latitude": 24.7120,
      "longitude": 46.6730,
      "updated_at": "2025-01-15T10:30:00Z"
    },
    "route_points": [
      {
        "latitude": 24.7000,
        "longitude": 46.6500,
        "timestamp": "2025-01-15T10:20:00Z",
        "speed": 45.0,
        "heading": 90.0
      },
      ...
    ],
    "total_distance_km": 15.3,
    "estimated_distance_km": 2.5,
    "current_status": "on_way_to_delivery",
    "estimated_arrival_time": "2025-01-15T10:35:00Z"
  }
}
```

## Frontend Integration

### Mobile App (Rider)

1. **Start Tracking**: When rider accepts an order, start polling location updates:
   ```javascript
   // Poll every 15 seconds
   setInterval(() => {
     updateLocation(orderId, {
       latitude: currentLat,
       longitude: currentLng,
       accuracy: locationAccuracy,
       speed: currentSpeed,
       heading: currentHeading
     });
   }, 15000);
   ```

2. **Stop Tracking**: Stop polling when delivery is completed or cancelled.

### Mobile App (Customer)

1. **Poll Tracking**: Poll tracking endpoint every 15 seconds:
   ```javascript
   // Poll every 15 seconds
   setInterval(() => {
     fetchTracking(orderId);
   }, 15000);
   ```

2. **Display on Map**: Use the `current_location` and `recent_route` data to display on map.

### Admin Dashboard

1. **Display Route**: Use the route endpoint to display full delivery route on map.
2. **Show Status**: Display current status, ETA, and distance information.

## Management Commands

### Cleanup Location History

Automatically clean up location history older than 30 days:

```bash
python manage.py cleanup_location_history
```

**Options:**
- `--days`: Number of days to keep (default: 30)
- `--dry-run`: Show what would be deleted without actually deleting

**Cron Job Setup:**
Add to crontab to run daily:
```cron
0 2 * * * cd /path/to/project && python manage.py cleanup_location_history
```

## Automatic Features

### Auto-Create Tracking
Tracking is automatically created when:
- A rider is assigned to an order
- Order status changes to `ready_for_delivery`

### Status Synchronization
Tracking status is automatically updated when:
- Order status changes
- Rider status changes (via order status transitions)

## Admin Interface

The admin interface provides:
- List view of all delivery tracking records
- Filter by status, active/inactive
- Search by order number, rider name, customer name
- Detailed view with all tracking information
- Location history view

## Data Retention

- **Location History**: Automatically deleted after 30 days
- **Delivery Tracking**: Kept permanently (for order history)
- **Cleanup Command**: Run daily via cron job

## ETA Calculation

ETA is calculated based on:
- Current distance to destination
- Current speed (if available) or average speed (40 km/h)
- Includes 10% buffer time for safety

## Distance Calculation

Uses Haversine formula for accurate distance calculation:
- Between GPS coordinates
- Total distance traveled
- Estimated distance to destination

## Error Handling

All endpoints include proper error handling:
- Permission checks (rider can only update their own orders)
- Validation (latitude/longitude ranges)
- Status checks (can't update completed deliveries)
- Graceful error messages

## Security

- Authentication required for all endpoints
- Role-based access control:
  - Riders can only update their own orders
  - Customers can only view their own orders
  - Admins can view all orders
  - Tailors can view their own orders

## Performance

- Indexed database queries for fast lookups
- Efficient location history queries (limited results)
- Optimized distance calculations
- Background cleanup process

## Testing

To test the feature:

1. Create an order with a rider assigned
2. Rider updates location via API
3. Customer polls tracking endpoint
4. Admin views route on dashboard
5. Verify location history is stored
6. Test cleanup command

## Future Enhancements

Potential improvements:
- WebSocket support for real-time updates (if needed)
- Geofencing for automatic status updates
- Route optimization suggestions
- Delivery time predictions based on historical data
- Push notifications for status changes

