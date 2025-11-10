# Rider System & Enhanced Order Flow Documentation

## Overview
This document describes the complete rider system implementation for the Zthob (Saudi Thobe) digital tailoring platform. The system enables riders to accept orders, take measurements, and deliver orders to customers.

## System Architecture

### Order Flow

#### 1. Fabric Only Orders (`fabric_only`)
```
Customer creates order → Payment (paid) → Rider accepts → 
Rider picks fabric from tailor → Rider marks ready_for_delivery → 
Rider delivers → Order status: delivered
```

#### 2. Fabric with Stitching Orders (`fabric_with_stitching`)
```
Customer creates order → Payment (paid) → Rider accepts → 
Rider goes to customer → Takes measurements → 
Order status: measuring → cutting → stitching → ready_for_delivery → 
Rider delivers → Order status: delivered
```

## API Endpoints

### Rider Authentication (`/api/riders/`)

#### 1. Register Rider
- **POST** `/api/riders/register/`
- **Description**: Register a new rider account
- **Request Body**:
  ```json
  {
    "username": "rider_username",
    "email": "rider@example.com",
    "password": "password123",
    "password_confirm": "password123",
    "phone_number": "+966501234567",
    "full_name": "Rider Full Name",
    "first_name": "First",
    "last_name": "Last"
  }
  ```
- **Response**: User data with JWT tokens

#### 2. Send OTP
- **POST** `/api/riders/send-otp/`
- **Description**: Send OTP to rider's phone number
- **Authentication**: Required (JWT)
- **Request Body**:
  ```json
  {
    "phone_number": "+966501234567"
  }
  ```

#### 3. Verify OTP
- **POST** `/api/riders/verify-otp/`
- **Description**: Verify OTP code
- **Authentication**: Required (JWT)
- **Request Body**:
  ```json
  {
    "otp_code": "123456"
  }
  ```

### Rider Profile (`/api/riders/`)

#### 4. Get Profile
- **GET** `/api/riders/profile/`
- **Description**: Get authenticated rider's profile
- **Authentication**: Required (JWT)

#### 5. Update Profile
- **PUT** `/api/riders/profile/`
- **Description**: Update rider profile
- **Authentication**: Required (JWT)
- **Request Body**:
  ```json
  {
    "full_name": "Updated Name",
    "vehicle_type": "motorcycle",
    "vehicle_number": "ABC123",
    "is_available": true,
    "current_latitude": 24.7136,
    "current_longitude": 46.6753
  }
  ```

### Rider Order Management (`/api/riders/orders/`)

#### 6. List Available Orders
- **GET** `/api/riders/orders/available/`
- **Description**: Get list of orders available for riders (payment_status=paid, no rider assigned)
- **Authentication**: Required (JWT)
- **Query Parameters**:
  - `status`: Filter by order status
  - `order_type`: Filter by order type (fabric_only, fabric_with_stitching)

#### 7. List My Orders
- **GET** `/api/riders/orders/my-orders/`
- **Description**: Get list of orders assigned to authenticated rider
- **Authentication**: Required (JWT)
- **Query Parameters**:
  - `status`: Filter by order status

#### 8. Get Order Details
- **GET** `/api/riders/orders/<order_id>/`
- **Description**: Get detailed information about a specific order
- **Authentication**: Required (JWT)

#### 9. Accept Order
- **POST** `/api/riders/orders/<order_id>/accept/`
- **Description**: Rider accepts an available order
- **Authentication**: Required (JWT)
- **Request Body**:
  ```json
  {
    "order_id": 1
  }
  ```
- **Behavior**:
  - For `fabric_only`: Status remains as is (rider picks from tailor)
  - For `fabric_with_stitching`: Status changes to `measuring` (rider needs to take measurements)

#### 10. Add Measurements
- **POST** `/api/riders/orders/<order_id>/measurements/`
- **Description**: Add measurements taken at customer location (for fabric_with_stitching orders only)
- **Authentication**: Required (JWT)
- **Request Body**:
  ```json
  {
    "measurements": {
      "chest": "42",
      "waist": "36",
      "shoulder": "18",
      "sleeve": "24",
      "length": "58"
    },
    "notes": "Customer prefers loose fit"
  }
  ```
- **Behavior**: Updates order status from `measuring` to `cutting` (tailor can now proceed)

#### 11. Update Order Status
- **PATCH** `/api/riders/orders/<order_id>/update-status/`
- **Description**: Update order status (ready_for_delivery, delivered)
- **Authentication**: Required (JWT)
- **Request Body**:
  ```json
  {
    "status": "ready_for_delivery",
    "notes": "Picked up from tailor"
  }
  ```
- **Status Options**:
  - `ready_for_delivery`: After picking from tailor (fabric_only) or after tailor completes (fabric_with_stitching)
  - `delivered`: After successful delivery

### Tailor Order Management (`/api/orders/tailor/`)

#### 12. List All Tailor Orders
- **GET** `/api/orders/tailor/my-orders/`
- **Description**: Get all orders assigned to authenticated tailor
- **Authentication**: Required (JWT)
- **Query Parameters**:
  - `payment_status`: Filter by payment status (use `paid` to see only paid orders)
  - `status`: Filter by order status
  - `order_type`: Filter by order type

#### 13. List Paid Orders
- **GET** `/api/orders/tailor/paid-orders/`
- **Description**: Get orders with payment_status=paid (ready for processing)
- **Authentication**: Required (JWT)
- **Query Parameters**:
  - `status`: Filter by order status
  - `order_type`: Filter by order type

#### 14. Get Tailor Order Details
- **GET** `/api/orders/tailor/<order_id>/`
- **Description**: Get detailed order information including rider measurements
- **Authentication**: Required (JWT)
- **Response Includes**:
  - Order details
  - Customer information
  - Delivery address
  - Rider information (if assigned)
  - **Rider measurements** (if taken)
  - Order items

## Database Models

### RiderProfile
- User profile information for riders
- Tracks vehicle information, availability, location
- Statistics: total_deliveries, rating

### RiderOrderAssignment
- Tracks rider assignments to orders
- Status: pending, accepted, in_progress, completed, cancelled
- Timeline: accepted_at, started_at, completed_at

### Order (Updated)
- Added `rider` field: ForeignKey to User (rider assigned)
- Added `rider_measurements` field: JSONField for measurements
- Added `measurement_taken_at` field: DateTimeField

## Order Status Flow

### Fabric Only Flow
1. **pending** → Customer creates order
2. **confirmed** → Tailor accepts order
3. **paid** → Payment completed (order available for rider)
4. **Rider accepts** → Order assigned to rider
5. **ready_for_delivery** → Rider picks fabric from tailor
6. **delivered** → Rider delivers to customer

### Fabric with Stitching Flow
1. **pending** → Customer creates order
2. **confirmed** → Tailor accepts order
3. **paid** → Payment completed (order available for rider)
4. **Rider accepts** → Status changes to **measuring**
5. **measuring** → Rider goes to customer location
6. **Rider adds measurements** → Status changes to **cutting**
7. **cutting** → Tailor cuts fabric
8. **stitching** → Tailor stitches garment
9. **ready_for_delivery** → Order ready for delivery
10. **delivered** → Rider delivers to customer

## Security & Permissions

- All rider endpoints require JWT authentication
- Role-based access control: Only users with `RIDER` role can access rider endpoints
- Order access control: Riders can only access orders assigned to them or available orders
- Phone verification required for riders

## Business Rules

1. **Order Assignment**:
   - Only orders with `payment_status='paid'` are available for riders
   - Only one rider can be assigned to an order
   - Rider must accept order before working on it

2. **Measurements**:
   - Only for `fabric_with_stitching` orders
   - Can only be added when order status is `measuring`
   - Once measurements are added, order status changes to `cutting` (tailor can proceed)

3. **Status Updates**:
   - Riders can update status to `ready_for_delivery` after picking from tailor
   - Riders can mark as `delivered` only when status is `ready_for_delivery`
   - All status changes are tracked in OrderStatusHistory

4. **Tailor Visibility**:
   - Tailors can see all their orders
   - Use `payment_status=paid` filter to see orders ready for processing
   - Rider measurements are visible in order details

## Migration Instructions

Run the following commands to create and apply migrations:

```bash
# Create migrations for riders app
python manage.py makemigrations riders

# Create migrations for orders app (for new fields)
python manage.py makemigrations orders

# Apply all migrations
python manage.py migrate
```

## Testing Checklist

- [ ] Rider registration works
- [ ] Phone verification works
- [ ] Rider can view available orders (paid, no rider)
- [ ] Rider can accept orders
- [ ] Rider can add measurements (fabric_with_stitching only)
- [ ] Rider can update order status
- [ ] Tailor can view paid orders
- [ ] Tailor can see rider measurements
- [ ] Order status flow works correctly for both order types
- [ ] Status history is created correctly
- [ ] Permissions are enforced correctly

## Next Steps

1. Run migrations
2. Test all endpoints
3. Add unit tests
4. Add integration tests
5. Update API documentation in Swagger
6. Add error handling improvements if needed

