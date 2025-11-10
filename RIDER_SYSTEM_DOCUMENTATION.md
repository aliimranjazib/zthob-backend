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
- **Description**: Get authenticated rider's profile with all information including `is_phone_verified` and `review_status`
- **Authentication**: Required (JWT)
- **Response Includes**:
  - Basic information (username, email, full_name, phone_number)
  - `is_phone_verified`: Phone verification status
  - `is_approved`: Whether profile is approved by admin
  - `review_status`: Current review status (draft, pending, approved, rejected)
  - National Identity / Iqama information
  - Driving License information
  - Vehicle Information
  - Insurance Details
  - Documents array with URLs
  - Statistics (total_deliveries, rating)
  - Location and availability status

#### 5. Update Profile
- **PUT** `/api/riders/profile/`
- **Description**: Update rider profile information
- **Authentication**: Required (JWT)
- **Request Body**:
  ```json
  {
    "full_name": "Updated Name",
    "phone_number": "+966501234567",
    "emergency_contact": "+966509876543",
    "iqama_number": "1234567890",
    "iqama_expiry_date": "2025-12-31",
    "license_number": "DL123456",
    "license_expiry_date": "2026-06-30",
    "license_type": "private",
    "vehicle_type": "motorcycle",
    "vehicle_plate_number_arabic": "أ ب ج ١٢٣",
    "vehicle_plate_number_english": "ABC123",
    "vehicle_make": "Honda",
    "vehicle_model": "CBR600",
    "vehicle_year": 2020,
    "vehicle_color": "Red",
    "vehicle_registration_number": "IST123456",
    "vehicle_registration_expiry_date": "2025-12-31",
    "insurance_provider": "Tawuniya",
    "insurance_policy_number": "POL123456",
    "insurance_expiry_date": "2025-12-31",
    "is_available": true,
    "current_latitude": 24.7136,
    "current_longitude": 46.6753
  }
  ```

#### 6. Submit Profile for Review
- **POST** `/api/riders/profile/submit/`
- **Description**: Submit rider profile for admin review. Profile must be complete with required fields.
- **Authentication**: Required (JWT)
- **Request Body**: Same as Update Profile
- **Required Fields for Submission**:
  - `full_name`
  - `iqama_number`
  - `phone_number`
  - `license_number`
  - `vehicle_type`
  - `vehicle_plate_number_english`
  - `vehicle_registration_number`
- **Behavior**: Changes review status from `draft` to `pending`

#### 7. Check Review Status
- **GET** `/api/riders/profile/status/`
- **Description**: Check the review status of rider profile
- **Authentication**: Required (JWT)
- **Response**:
  ```json
  {
    "review_status": "pending",
    "submitted_at": "2024-01-15T10:30:00Z",
    "reviewed_at": null,
    "rejection_reason": null
  }
  ```

### Rider Document Management (`/api/riders/documents/`)

#### 8. Upload Document
- **POST** `/api/riders/documents/upload/`
- **Description**: Upload rider documents (Iqama, License, Istimara, Insurance)
- **Authentication**: Required (JWT)
- **Content-Type**: `multipart/form-data`
- **Request Body**:
  - `document_type`: One of: `iqama_front`, `iqama_back`, `license_front`, `license_back`, `istimara_front`, `istimara_back`, `insurance`
  - `document_image`: Image file (JPG, JPEG, PNG, PDF)
- **Response**: Document object with URL and verification status

#### 9. List Documents
- **GET** `/api/riders/documents/`
- **Description**: Get all documents uploaded by authenticated rider
- **Authentication**: Required (JWT)
- **Response**: Array of document objects with URLs

#### 10. Delete Document
- **DELETE** `/api/riders/documents/<document_id>/`
- **Description**: Delete a specific document
- **Authentication**: Required (JWT)

### Rider Order Management (`/api/riders/orders/`)

#### 11. List Available Orders
- **GET** `/api/riders/orders/available/`
- **Description**: Get list of orders available for riders (payment_status=paid, no rider assigned)
- **Authentication**: Required (JWT)
- **Query Parameters**:
  - `status`: Filter by order status
  - `order_type`: Filter by order type (fabric_only, fabric_with_stitching)

#### 12. List My Orders
- **GET** `/api/riders/orders/my-orders/`
- **Description**: Get list of orders assigned to authenticated rider
- **Authentication**: Required (JWT)
- **Query Parameters**:
  - `status`: Filter by order status

#### 13. Get Order Details
- **GET** `/api/riders/orders/<order_id>/`
- **Description**: Get detailed information about a specific order
- **Authentication**: Required (JWT)

#### 14. Accept Order
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

#### 15. Add Measurements
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

#### 16. Update Order Status
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

### Rider Admin Review (`/api/riders/admin/`)

#### 17. List Rider Reviews (Admin Only)
- **GET** `/api/riders/admin/reviews/`
- **Description**: Get all rider profiles pending review (Admin only)
- **Authentication**: Required (JWT, Admin only)
- **Query Parameters**:
  - `status`: Filter by review status (default: `pending`)

#### 18. Get Review Details (Admin Only)
- **GET** `/api/riders/admin/reviews/<pk>/`
- **Description**: Get detailed information about a specific rider review
- **Authentication**: Required (JWT, Admin only)

#### 19. Approve/Reject Rider (Admin Only)
- **PUT** `/api/riders/admin/reviews/<pk>/`
- **Description**: Approve or reject rider profile
- **Authentication**: Required (JWT, Admin only)
- **Request Body**:
  ```json
  {
    "review_status": "approved",
    "rejection_reason": ""  // Required if rejected
  }
  ```

### Tailor Order Management (`/api/orders/tailor/`)

#### 20. List All Tailor Orders
- **GET** `/api/orders/tailor/my-orders/`
- **Description**: Get all orders assigned to authenticated tailor
- **Authentication**: Required (JWT)
- **Query Parameters**:
  - `payment_status`: Filter by payment status (use `paid` to see only paid orders)
  - `status`: Filter by order status
  - `order_type`: Filter by order type

#### 21. List Paid Orders
- **GET** `/api/orders/tailor/paid-orders/`
- **Description**: Get orders with payment_status=paid (ready for processing)
- **Authentication**: Required (JWT)
- **Query Parameters**:
  - `status`: Filter by order status
  - `order_type`: Filter by order type

#### 22. Get Tailor Order Details
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
Comprehensive rider profile model with the following sections:

#### Personal Information
- `full_name`: Full name of the rider
- `phone_number`: Primary contact number
- `emergency_contact`: Emergency contact number

#### National Identity / Iqama
- `iqama_number`: 10-digit Iqama number (validated, unique)
- `iqama_expiry_date`: Expiry date of Iqama/National ID

#### Driving License
- `license_number`: Driving license number
- `license_expiry_date`: License expiry date
- `license_type`: Type of license (Private, General, Motorcycle, Commercial)

#### Vehicle Information
- `vehicle_type`: Type of vehicle (Motorcycle, Car, Bicycle, Truck, Van, Other)
- `vehicle_plate_number_arabic`: Plate number in Arabic
- `vehicle_plate_number_english`: Plate number in English
- `vehicle_make`: Vehicle brand (e.g., Toyota, Honda)
- `vehicle_model`: Vehicle model (e.g., Camry, Accord)
- `vehicle_year`: Manufacturing year
- `vehicle_color`: Vehicle color
- `vehicle_registration_number`: Istimara number
- `vehicle_registration_expiry_date`: Istimara expiry date

#### Insurance Details
- `insurance_provider`: Insurance company name
- `insurance_policy_number`: Policy number
- `insurance_expiry_date`: Insurance expiry date

#### Status & Location
- `is_active`: Whether rider is currently active
- `is_available`: Whether rider is available for new orders
- `current_latitude`: Current GPS latitude
- `current_longitude`: Current GPS longitude

#### Statistics
- `total_deliveries`: Total number of completed deliveries
- `rating`: Average rating from customers

#### Properties
- `is_approved`: Property that checks if `review.review_status == 'approved'`
- `review_status`: Property that returns current review status

### RiderProfileReview
Tracks the review and approval process for rider profiles:
- `profile`: OneToOne relationship with RiderProfile
- `review_status`: draft, pending, approved, rejected
- `submitted_at`: When profile was submitted for review
- `reviewed_at`: When admin reviewed the profile
- `reviewed_by`: Admin who reviewed (ForeignKey to User)
- `rejection_reason`: Reason for rejection if applicable

### RiderDocument
Stores uploaded documents for riders:
- `rider_profile`: ForeignKey to RiderProfile
- `document_type`: Type of document (iqama_front, iqama_back, license_front, license_back, istimara_front, istimara_back, insurance)
- `document_image`: Image file (JPG, JPEG, PNG, PDF)
- `is_verified`: Whether document has been verified by admin
- `verified_at`: When document was verified
- `verified_by`: Admin who verified (ForeignKey to User)
- `notes`: Admin notes about the document
- Unique constraint: One document per type per rider

### RiderOrderAssignment
Tracks rider assignments to orders:
- `order`: OneToOne relationship with Order
- `rider`: ForeignKey to User (rider assigned)
- `status`: pending, accepted, in_progress, completed, cancelled
- `accepted_at`: When rider accepted the order
- `started_at`: When rider started working on the order
- `completed_at`: When delivery was completed
- `notes`: Additional notes from the rider

### Order (Updated)
- `rider`: ForeignKey to User (rider assigned to order)
- `rider_measurements`: JSONField for measurements taken by rider
- `measurement_taken_at`: DateTimeField for when measurements were taken

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
- **Admin Approval Required**: Riders must be approved by admin before they can accept orders
- Document verification: Documents are verified by admin before approval

## Business Rules

1. **Rider Approval**:
   - Rider must register and complete profile
   - Rider must upload required documents (Iqama, License, Istimara, Insurance)
   - Rider must submit profile for review
   - Admin must approve rider before they can accept orders
   - Only approved riders can view available orders and accept orders

2. **Profile Submission**:
   - Required fields must be filled before submission: full_name, iqama_number, phone_number, license_number, vehicle_type, vehicle_plate_number_english, vehicle_registration_number
   - Profile status changes from `draft` to `pending` upon submission
   - Rider can resubmit after rejection (after fixing issues)

3. **Document Management**:
   - Riders can upload multiple document types
   - Each document type can only be uploaded once (unique constraint)
   - Uploading a new document of the same type replaces the old one
   - Documents are verified by admin
   - Document verification status is tracked

4. **Order Assignment**:
   - Only orders with `payment_status='paid'` are available for riders
   - Only approved riders can see available orders
   - Only one rider can be assigned to an order
   - Rider must accept order before working on it

5. **Measurements**:
   - Only for `fabric_with_stitching` orders
   - Can only be added when order status is `measuring`
   - Once measurements are added, order status changes to `cutting` (tailor can proceed)

6. **Status Updates**:
   - Riders can update status to `ready_for_delivery` after picking from tailor
   - Riders can mark as `delivered` only when status is `ready_for_delivery`
   - All status changes are tracked in OrderStatusHistory

7. **Tailor Visibility**:
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

## Validation Rules

### Iqama Number
- Must be exactly 10 digits
- Must be unique across all riders
- Validated using RegexValidator: `^\d{10}$`

### Required Fields for Profile Submission
- `full_name`: Required
- `iqama_number`: Required (10 digits)
- `phone_number`: Required
- `license_number`: Required
- `vehicle_type`: Required
- `vehicle_plate_number_english`: Required
- `vehicle_registration_number`: Required

### Document Types
Valid document types:
- `iqama_front`: Iqama front side
- `iqama_back`: Iqama back side
- `license_front`: Driving license front
- `license_back`: Driving license back
- `istimara_front`: Vehicle registration (Istimara) front
- `istimara_back`: Vehicle registration (Istimara) back
- `insurance`: Insurance card/image

### Document File Types
- Accepted formats: JPG, JPEG, PNG, PDF
- Validated using FileExtensionValidator

## cURL Examples

All examples use `http://localhost:8000` as the base URL. Replace with your actual server URL in production.

**Note**: Replace `YOUR_ACCESS_TOKEN` with the actual JWT access token received after login/registration.

### Rider Authentication

#### 1. Register Rider
```bash
curl -X POST http://localhost:8000/api/riders/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "rider_username",
    "email": "rider@example.com",
    "password": "password123",
    "password_confirm": "password123",
    "phone_number": "+966501234567",
    "full_name": "Rider Full Name",
    "first_name": "First",
    "last_name": "Last"
  }'
```

#### 2. Send OTP
```bash
curl -X POST http://localhost:8000/api/riders/send-otp/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "phone_number": "+966501234567"
  }'
```

#### 3. Verify OTP
```bash
curl -X POST http://localhost:8000/api/riders/verify-otp/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "otp_code": "123456"
  }'
```

### Rider Profile

#### 4. Get Profile
```bash
curl -X GET http://localhost:8000/api/riders/profile/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### 5. Update Profile
```bash
curl -X PUT http://localhost:8000/api/riders/profile/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "full_name": "Updated Name",
    "phone_number": "+966501234567",
    "emergency_contact": "+966509876543",
    "iqama_number": "1234567890",
    "iqama_expiry_date": "2025-12-31",
    "license_number": "DL123456",
    "license_expiry_date": "2026-06-30",
    "license_type": "private",
    "vehicle_type": "motorcycle",
    "vehicle_plate_number_arabic": "أ ب ج ١٢٣",
    "vehicle_plate_number_english": "ABC123",
    "vehicle_make": "Honda",
    "vehicle_model": "CBR600",
    "vehicle_year": 2020,
    "vehicle_color": "Red",
    "vehicle_registration_number": "IST123456",
    "vehicle_registration_expiry_date": "2025-12-31",
    "insurance_provider": "Tawuniya",
    "insurance_policy_number": "POL123456",
    "insurance_expiry_date": "2025-12-31",
    "is_available": true,
    "current_latitude": 24.7136,
    "current_longitude": 46.6753
  }'
```

#### 6. Submit Profile for Review
```bash
curl -X POST http://localhost:8000/api/riders/profile/submit/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "full_name": "Rider Full Name",
    "phone_number": "+966501234567",
    "iqama_number": "1234567890",
    "license_number": "DL123456",
    "vehicle_type": "motorcycle",
    "vehicle_plate_number_english": "ABC123",
    "vehicle_registration_number": "IST123456"
  }'
```

#### 7. Check Review Status
```bash
curl -X GET http://localhost:8000/api/riders/profile/status/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Rider Document Management

#### 8. Upload Document
```bash
curl -X POST http://localhost:8000/api/riders/documents/upload/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "document_type=iqama_front" \
  -F "document_image=@/path/to/iqama_front.jpg"
```

**Other document types:**
- `iqama_back`
- `license_front`
- `license_back`
- `istimara_front`
- `istimara_back`
- `insurance`

**Example for multiple documents:**
```bash
# Upload Iqama Front
curl -X POST http://localhost:8000/api/riders/documents/upload/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "document_type=iqama_front" \
  -F "document_image=@/path/to/iqama_front.jpg"

# Upload Iqama Back
curl -X POST http://localhost:8000/api/riders/documents/upload/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "document_type=iqama_back" \
  -F "document_image=@/path/to/iqama_back.jpg"

# Upload License Front
curl -X POST http://localhost:8000/api/riders/documents/upload/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "document_type=license_front" \
  -F "document_image=@/path/to/license_front.jpg"

# Upload License Back
curl -X POST http://localhost:8000/api/riders/documents/upload/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "document_type=license_back" \
  -F "document_image=@/path/to/license_back.jpg"

# Upload Istimara Front
curl -X POST http://localhost:8000/api/riders/documents/upload/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "document_type=istimara_front" \
  -F "document_image=@/path/to/istimara_front.jpg"

# Upload Istimara Back
curl -X POST http://localhost:8000/api/riders/documents/upload/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "document_type=istimara_back" \
  -F "document_image=@/path/to/istimara_back.jpg"

# Upload Insurance
curl -X POST http://localhost:8000/api/riders/documents/upload/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "document_type=insurance" \
  -F "document_image=@/path/to/insurance.jpg"
```

#### 9. List Documents
```bash
curl -X GET http://localhost:8000/api/riders/documents/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### 10. Delete Document
```bash
curl -X DELETE http://localhost:8000/api/riders/documents/1/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Rider Order Management

#### 11. List Available Orders
```bash
# Get all available orders
curl -X GET http://localhost:8000/api/riders/orders/available/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Filter by status
curl -X GET "http://localhost:8000/api/riders/orders/available/?status=pending" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Filter by order type
curl -X GET "http://localhost:8000/api/riders/orders/available/?order_type=fabric_only" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Combined filters
curl -X GET "http://localhost:8000/api/riders/orders/available/?status=pending&order_type=fabric_with_stitching" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### 12. List My Orders
```bash
# Get all my orders
curl -X GET http://localhost:8000/api/riders/orders/my-orders/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Filter by status
curl -X GET "http://localhost:8000/api/riders/orders/my-orders/?status=measuring" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### 13. Get Order Details
```bash
curl -X GET http://localhost:8000/api/riders/orders/1/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### 14. Accept Order
```bash
curl -X POST http://localhost:8000/api/riders/orders/1/accept/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "order_id": 1
  }'
```

#### 15. Add Measurements
```bash
curl -X POST http://localhost:8000/api/riders/orders/1/measurements/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "measurements": {
      "chest": "42",
      "waist": "36",
      "shoulder": "18",
      "sleeve": "24",
      "length": "58"
    },
    "notes": "Customer prefers loose fit"
  }'
```

#### 16. Update Order Status
```bash
# Mark as ready for delivery
curl -X PATCH http://localhost:8000/api/riders/orders/1/update-status/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "status": "ready_for_delivery",
    "notes": "Picked up from tailor"
  }'

# Mark as delivered
curl -X PATCH http://localhost:8000/api/riders/orders/1/update-status/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "status": "delivered",
    "notes": "Successfully delivered to customer"
  }'
```

### Rider Admin Review (Admin Only)

#### 17. List Rider Reviews
```bash
# Get all pending reviews
curl -X GET http://localhost:8000/api/riders/admin/reviews/ \
  -H "Authorization: Bearer YOUR_ADMIN_ACCESS_TOKEN"

# Filter by status
curl -X GET "http://localhost:8000/api/riders/admin/reviews/?status=approved" \
  -H "Authorization: Bearer YOUR_ADMIN_ACCESS_TOKEN"
```

#### 18. Get Review Details
```bash
curl -X GET http://localhost:8000/api/riders/admin/reviews/1/ \
  -H "Authorization: Bearer YOUR_ADMIN_ACCESS_TOKEN"
```

#### 19. Approve/Reject Rider
```bash
# Approve rider
curl -X PUT http://localhost:8000/api/riders/admin/reviews/1/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ADMIN_ACCESS_TOKEN" \
  -d '{
    "review_status": "approved"
  }'

# Reject rider
curl -X PUT http://localhost:8000/api/riders/admin/reviews/1/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ADMIN_ACCESS_TOKEN" \
  -d '{
    "review_status": "rejected",
    "rejection_reason": "Documents are not clear. Please upload better quality images."
  }'
```

### Tailor Order Management

#### 20. List All Tailor Orders
```bash
# Get all orders
curl -X GET http://localhost:8000/api/orders/tailor/my-orders/ \
  -H "Authorization: Bearer YOUR_TAILOR_ACCESS_TOKEN"

# Filter by payment status
curl -X GET "http://localhost:8000/api/orders/tailor/my-orders/?payment_status=paid" \
  -H "Authorization: Bearer YOUR_TAILOR_ACCESS_TOKEN"

# Filter by order status
curl -X GET "http://localhost:8000/api/orders/tailor/my-orders/?status=cutting" \
  -H "Authorization: Bearer YOUR_TAILOR_ACCESS_TOKEN"

# Combined filters
curl -X GET "http://localhost:8000/api/orders/tailor/my-orders/?payment_status=paid&status=measuring&order_type=fabric_with_stitching" \
  -H "Authorization: Bearer YOUR_TAILOR_ACCESS_TOKEN"
```

#### 21. List Paid Orders
```bash
# Get all paid orders
curl -X GET http://localhost:8000/api/orders/tailor/paid-orders/ \
  -H "Authorization: Bearer YOUR_TAILOR_ACCESS_TOKEN"

# Filter by status
curl -X GET "http://localhost:8000/api/orders/tailor/paid-orders/?status=cutting" \
  -H "Authorization: Bearer YOUR_TAILOR_ACCESS_TOKEN"

# Filter by order type
curl -X GET "http://localhost:8000/api/orders/tailor/paid-orders/?order_type=fabric_with_stitching" \
  -H "Authorization: Bearer YOUR_TAILOR_ACCESS_TOKEN"
```

#### 22. Get Tailor Order Details
```bash
curl -X GET http://localhost:8000/api/orders/tailor/1/ \
  -H "Authorization: Bearer YOUR_TAILOR_ACCESS_TOKEN"
```

### Complete Workflow Example

Here's a complete workflow example from registration to order delivery:

```bash
# 1. Register as rider
REGISTER_RESPONSE=$(curl -s -X POST http://localhost:8000/api/riders/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "rider_test",
    "email": "rider@test.com",
    "password": "password123",
    "password_confirm": "password123",
    "phone_number": "+966501234567",
    "full_name": "Test Rider",
    "first_name": "Test",
    "last_name": "Rider"
  }')

# Extract access token (adjust based on your response format)
ACCESS_TOKEN=$(echo $REGISTER_RESPONSE | jq -r '.data.access')

# 2. Send OTP
curl -X POST http://localhost:8000/api/riders/send-otp/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{"phone_number": "+966501234567"}'

# 3. Verify OTP (use actual OTP received)
curl -X POST http://localhost:8000/api/riders/verify-otp/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{"otp_code": "123456"}'

# 4. Update profile with required information
curl -X PUT http://localhost:8000/api/riders/profile/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
    "full_name": "Test Rider",
    "phone_number": "+966501234567",
    "iqama_number": "1234567890",
    "license_number": "DL123456",
    "vehicle_type": "motorcycle",
    "vehicle_plate_number_english": "ABC123",
    "vehicle_registration_number": "IST123456"
  }'

# 5. Upload documents
curl -X POST http://localhost:8000/api/riders/documents/upload/ \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "document_type=iqama_front" \
  -F "document_image=@iqama_front.jpg"

# 6. Submit profile for review
curl -X POST http://localhost:8000/api/riders/profile/submit/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
    "full_name": "Test Rider",
    "phone_number": "+966501234567",
    "iqama_number": "1234567890",
    "license_number": "DL123456",
    "vehicle_type": "motorcycle",
    "vehicle_plate_number_english": "ABC123",
    "vehicle_registration_number": "IST123456"
  }'

# 7. Check review status
curl -X GET http://localhost:8000/api/riders/profile/status/ \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# 8. After admin approval, view available orders
curl -X GET http://localhost:8000/api/riders/orders/available/ \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# 9. Accept an order
curl -X POST http://localhost:8000/api/riders/orders/1/accept/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{"order_id": 1}'

# 10. For fabric_with_stitching orders, add measurements
curl -X POST http://localhost:8000/api/riders/orders/1/measurements/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
    "measurements": {
      "chest": "42",
      "waist": "36",
      "shoulder": "18",
      "sleeve": "24",
      "length": "58"
    },
    "notes": "Customer prefers loose fit"
  }'

# 11. Update order status to ready for delivery
curl -X PATCH http://localhost:8000/api/riders/orders/1/update-status/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
    "status": "ready_for_delivery",
    "notes": "Picked up from tailor"
  }'

# 12. Mark order as delivered
curl -X PATCH http://localhost:8000/api/riders/orders/1/update-status/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
    "status": "delivered",
    "notes": "Successfully delivered to customer"
  }'
```

## Testing Checklist

- [ ] Rider registration works
- [ ] Phone verification works
- [ ] Rider can update profile with all fields
- [ ] Rider can upload documents (all types)
- [ ] Rider can list documents
- [ ] Rider can delete documents
- [ ] Rider can submit profile for review
- [ ] Rider can check review status
- [ ] Admin can view pending reviews
- [ ] Admin can approve/reject riders
- [ ] Approved riders can view available orders
- [ ] Unapproved riders cannot view available orders
- [ ] Rider can accept orders (only if approved)
- [ ] Rider can add measurements (fabric_with_stitching only)
- [ ] Rider can update order status
- [ ] Tailor can view paid orders
- [ ] Tailor can see rider measurements
- [ ] Order status flow works correctly for both order types
- [ ] Status history is created correctly
- [ ] Permissions are enforced correctly
- [ ] Document verification works
- [ ] Profile GET response includes `is_phone_verified` and `review_status`

## Next Steps

1. Run migrations
2. Test all endpoints
3. Add unit tests
4. Add integration tests
5. Update API documentation in Swagger
6. Add error handling improvements if needed

