# Swagger UI Access Guide

## How to Access Swagger UI

Your Django REST Framework API documentation is available via Swagger UI. Here's how to access it:

### 1. Start Your Django Server

```bash
python manage.py runserver
```

### 2. Access Swagger UI

Open your browser and navigate to:

**Swagger UI (Interactive):**
```
http://localhost:8000/api/schema/swagger-ui/
```

**ReDoc (Alternative Documentation):**
```
http://localhost:8000/api/schema/redoc/
```

**OpenAPI Schema (JSON):**
```
http://localhost:8000/api/schema/
```

### 3. For Production Server

If your server is deployed, replace `localhost:8000` with your domain:

```
https://your-domain.com/api/schema/swagger-ui/
```

## Using Swagger UI

### Authentication

1. **Click "Authorize" button** (top right)
2. **Enter your JWT token:**
   - Format: `Bearer <your_access_token>`
   - Or just: `<your_access_token>`
3. **Click "Authorize"**
4. **Click "Close"**

### Testing Delivery Tracking Endpoints

#### 1. Rider - Update Location

1. Find **`POST /api/deliveries/rider/orders/{order_id}/update-location/`**
2. Click **"Try it out"**
3. Fill in:
   - `order_id`: Your order ID (e.g., `1`)
   - Request body:
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
4. Click **"Execute"**
5. View response below

#### 2. Customer - Get Tracking

1. Find **`GET /api/deliveries/customer/orders/{order_id}/tracking/`**
2. Click **"Try it out"**
3. Enter `order_id` (e.g., `1`)
4. Click **"Execute"**
5. View response with tracking data

#### 3. Admin - Get Route Data

1. Find **`GET /api/deliveries/admin/orders/{order_id}/tracking/route/`**
2. Click **"Try it out"**
3. Enter `order_id`
4. Click **"Execute"**
5. View route visualization data

## Finding Delivery Tracking Endpoints

In Swagger UI, look for these sections:

1. **Rider Delivery Tracking** - Rider endpoints
2. **Customer Delivery Tracking** - Customer endpoints
3. **Admin Delivery Tracking** - Admin/Tailor endpoints

Or use the search box (top right) to search for:
- "delivery"
- "tracking"
- "location"

## Swagger UI Features

### 1. Interactive Testing
- Test endpoints directly from browser
- No need for Postman (but Postman is still useful for automation)

### 2. Schema Documentation
- See all request/response schemas
- View required vs optional fields
- See data types and validation rules

### 3. Try It Out
- Fill in parameters
- Send requests
- See responses
- View request/response examples

### 4. Authentication
- Set JWT token once
- All requests use the same token
- Easy to test authenticated endpoints

## Example Workflow

### Testing Complete Flow

1. **Login** (via accounts endpoint) to get access token
2. **Authorize** in Swagger UI with the token
3. **Rider updates location:**
   - POST `/api/deliveries/rider/orders/1/update-location/`
   - Send GPS coordinates
4. **Customer views tracking:**
   - GET `/api/deliveries/customer/orders/1/tracking/`
   - See rider's location
5. **Admin views route:**
   - GET `/api/deliveries/admin/orders/1/tracking/route/`
   - See full route data

## Troubleshooting

### Swagger UI Not Loading

1. **Check server is running:**
   ```bash
   python manage.py runserver
   ```

2. **Check URL is correct:**
   - Should be: `http://localhost:8000/api/schema/swagger-ui/`
   - Not: `http://localhost:8000/swagger-ui/`

3. **Check drf-spectacular is installed:**
   ```bash
   pip install drf-spectacular
   ```

### Authentication Not Working

1. **Check token format:**
   - Should be: `Bearer <token>` or just `<token>`
   - Make sure token is valid and not expired

2. **Get new token:**
   - Login again via accounts endpoint
   - Copy new access token
   - Update in Swagger UI

### Endpoints Not Showing

1. **Check deliveries app is in INSTALLED_APPS:**
   - Should be in `settings.py`: `"apps.deliveries"`

2. **Check URLs are registered:**
   - Should be in `zthob/urls.py`: `path('api/deliveries/', include('apps.deliveries.urls'))`

3. **Restart server:**
   ```bash
   python manage.py runserver
   ```

## Screenshots Guide

### Main Swagger UI Page
- Lists all API endpoints
- Grouped by app/feature
- Searchable

### Endpoint Details
- Request method and path
- Parameters (path, query, body)
- Request body schema
- Response schemas
- Example values

### Try It Out
- Fill in parameters
- Execute request
- See response
- View curl command

## Alternative: ReDoc

ReDoc provides a cleaner, more readable documentation view:

```
http://localhost:8000/api/schema/redoc/
```

**Features:**
- Better for reading documentation
- Less interactive (no "Try it out")
- Cleaner layout
- Good for sharing with team

## Quick Links

- **Swagger UI**: `http://localhost:8000/api/schema/swagger-ui/`
- **ReDoc**: `http://localhost:8000/api/schema/redoc/`
- **OpenAPI Schema**: `http://localhost:8000/api/schema/`

## Tips

1. **Bookmark Swagger UI** for quick access
2. **Use search** to find endpoints quickly
3. **Save responses** for reference
4. **Test with different order IDs** to see various states
5. **Check response schemas** to understand data structure

