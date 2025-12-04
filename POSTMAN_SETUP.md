# Postman Collection Setup Guide

## Importing the Collection

1. **Open Postman**
2. Click **Import** button (top left)
3. Select the file: `Delivery_Tracking_API.postman_collection.json`
4. Click **Import**

## Setting Up Environment Variables

### Create Environment

1. Click **Environments** in the left sidebar
2. Click **+** to create a new environment
3. Name it: `Zthob Local` or `Zthob Production`

### Set Variables

Add these variables:

| Variable | Value | Description |
|----------|-------|-------------|
| `base_url` | `http://localhost:8000` | Your API base URL (change for production) |
| `access_token` | (leave empty) | JWT token (will be set after login) |

### For Production

If testing against production server:
- `base_url`: `https://your-production-domain.com`

## Getting Access Token

### Option 1: Use Authentication Endpoint

1. Go to your authentication endpoint (e.g., `/api/accounts/login/`)
2. Send POST request with credentials
3. Copy the `access_token` from response
4. Set it in environment variable `access_token`

### Option 2: Manual Setup

1. In Postman, select your environment
2. Click **Edit** (pencil icon)
3. Set `access_token` value
4. Click **Save**

## Using the Collection

### Rider Endpoints

1. **Update Location**
   - Set `order_id` in URL path (e.g., `:order_id` = `1`)
   - Update request body with GPS coordinates
   - Send request (should be called every 15 seconds)

2. **Get Tracking (Rider)**
   - Set `order_id` in URL path
   - Send GET request
   - View detailed tracking information

### Customer Endpoints

1. **Get Tracking (Customer)**
   - Set `order_id` in URL path
   - Send GET request
   - View real-time tracking data

2. **Get Location History**
   - Set `order_id` in URL path
   - Optionally set `limit` query parameter
   - Send GET request

### Admin/Tailor Endpoints

1. **Get Tracking (Admin/Tailor)**
   - Set `order_id` in URL path
   - Send GET request
   - View full tracking details with history

2. **Get Route Data**
   - Set `order_id` in URL path
   - Send GET request
   - Get route visualization data

## Testing

### Test Scripts

Each request includes test scripts that automatically verify:
- Status code is 200
- Response has expected structure
- Response time is acceptable

### View Test Results

After sending a request:
1. Click **Test Results** tab
2. See which tests passed/failed

## Example Request Bodies

### Update Location (Rider)

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

**Required:**
- `latitude` (-90 to 90)
- `longitude` (-180 to 180)

**Optional:**
- `accuracy` (meters)
- `speed` (km/h)
- `heading` (degrees 0-360)
- `status` (string)

## Troubleshooting

### 401 Unauthorized
- Check if `access_token` is set correctly
- Verify token hasn't expired
- Re-authenticate and get new token

### 403 Forbidden
- Verify user role matches endpoint requirement
- Rider endpoints require `RIDER` role
- Customer endpoints require `USER` role
- Admin endpoints require `ADMIN` or `TAILOR` role

### 404 Not Found
- Check if `order_id` exists
- Verify order has a rider assigned (for tracking)
- Check base URL is correct

### 400 Bad Request
- Verify request body format is correct
- Check latitude/longitude are within valid ranges
- Ensure required fields are provided

## Collection Structure

```
Delivery Tracking API
├── Rider Endpoints
│   ├── Update Location (POST)
│   └── Get Tracking (GET)
├── Customer Endpoints
│   ├── Get Tracking (GET)
│   └── Get Location History (GET)
└── Admin/Tailor Endpoints
    ├── Get Tracking (GET)
    └── Get Route Data (GET)
```

## Quick Start

1. Import collection
2. Create environment with `base_url` and `access_token`
3. Get access token from login endpoint
4. Set `order_id` in request URLs
5. Start testing!

## Notes

- All endpoints require authentication (JWT token)
- Rider can only update their own assigned orders
- Customer can only view their own orders
- Admin can view all orders
- Tailor can view their own orders
- Location updates should be sent every 15 seconds
- Tracking should be polled every 15 seconds

