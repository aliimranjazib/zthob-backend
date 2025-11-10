# Zthob Backend - Saudi Thobe Digital Tailoring Platform

A comprehensive Django REST Framework backend for digitizing the traditional Saudi Thobe tailoring system. This platform connects customers, tailors, and riders to streamline the entire process from order placement to delivery.

## 🚀 Features

### Core Functionality
- **Customer Management**: Profile management, address management, family member profiles
- **Tailor Management**: Shop profiles, fabric catalog, service areas, profile review system
- **Order Management**: Complete order lifecycle from creation to delivery
- **Rider Management**: Professional rider onboarding with document verification and order delivery
- **Authentication**: JWT-based authentication with phone verification
- **Admin Panel**: Professional Django admin interface with advanced filtering and bulk actions

### Rider System
- **Comprehensive Profile**: National ID/Iqama, driving license, vehicle information, insurance details
- **Document Management**: Upload and verify Iqama, License, Istimara, and Insurance documents
- **Admin Approval**: Manual admin review and approval process (similar to tailor system)
- **Order Management**: Accept orders, take measurements, update order status
- **Location Tracking**: Real-time location tracking for delivery management

## 📋 Table of Contents

- [Installation](#installation)
- [Configuration](#configuration)
- [API Documentation](#api-documentation)
- [Rider System](#rider-system)
- [Order Flow](#order-flow)
- [Admin Interface](#admin-interface)
- [Database Models](#database-models)

## 🛠️ Installation

### Prerequisites
- Python 3.8+
- PostgreSQL (recommended) or SQLite (development)
- pip or uv

### Setup Steps

1. **Clone the repository**
```bash
git clone <repository-url>
cd zthob-backend
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
# OR using uv
uv pip install -r requirements.txt
```

4. **Configure environment variables**
```bash
cp env.template .env
# Edit .env with your configuration
```

5. **Run migrations**
```bash
python manage.py makemigrations
python manage.py migrate
```

6. **Create superuser**
```bash
python manage.py createsuperuser
```

7. **Run development server**
```bash
python manage.py runserver
```

## ⚙️ Configuration

### Environment Variables

Key environment variables (see `env.template` for full list):
- `SECRET_KEY`: Django secret key
- `DEBUG`: Debug mode (True/False)
- `DATABASE_URL`: Database connection string
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts

## 📚 API Documentation

### Base URL
```
http://localhost:8000/api/
```

### API Endpoints

#### Authentication (`/api/accounts/`)
- `POST /api/accounts/register/` - User registration
- `POST /api/accounts/login/` - User login (JWT tokens)
- `POST /api/accounts/send-otp/` - Send OTP for phone verification
- `POST /api/accounts/verify-otp/` - Verify OTP code

#### Rider APIs (`/api/riders/`)

**Authentication:**
- `POST /api/riders/register/` - Register new rider
- `POST /api/riders/send-otp/` - Send OTP to rider phone
- `POST /api/riders/verify-otp/` - Verify rider OTP

**Profile Management:**
- `GET /api/riders/profile/` - Get rider profile (includes `is_phone_verified`, `review_status`)
- `PUT /api/riders/profile/` - Update rider profile
- `POST /api/riders/profile/submit/` - Submit profile for admin review
- `GET /api/riders/profile/status/` - Check review status

**Document Management:**
- `POST /api/riders/documents/upload/` - Upload document (Iqama, License, Istimara, Insurance)
- `GET /api/riders/documents/` - List all documents
- `DELETE /api/riders/documents/<id>/` - Delete document

**Order Management:**
- `GET /api/riders/orders/available/` - List available orders (paid, no rider assigned)
- `GET /api/riders/orders/my-orders/` - List rider's assigned orders
- `GET /api/riders/orders/<order_id>/` - Get order details
- `POST /api/riders/orders/<order_id>/accept/` - Accept order
- `POST /api/riders/orders/<order_id>/measurements/` - Add measurements (fabric_with_stitching)
- `PATCH /api/riders/orders/<order_id>/update-status/` - Update order status

**Admin Review (Admin only):**
- `GET /api/riders/admin/reviews/` - List all rider reviews
- `GET /api/riders/admin/reviews/<pk>/` - Get review details
- `PUT /api/riders/admin/reviews/<pk>/` - Approve/reject rider

#### Order APIs (`/api/orders/`)
- `GET /api/orders/` - List all orders
- `POST /api/orders/create/` - Create new order
- `GET /api/orders/<order_id>/` - Get order details
- `PATCH /api/orders/<order_id>/status/` - Update order status
- `GET /api/orders/customer/my-orders/` - Customer's orders
- `GET /api/orders/tailor/my-orders/` - Tailor's orders
- `GET /api/orders/tailor/paid-orders/` - Tailor's paid orders
- `GET /api/orders/tailor/<order_id>/` - Tailor order details (includes rider measurements)

### Swagger Documentation

Access interactive API documentation:
- Swagger UI: `http://localhost:8000/api/schema/swagger-ui/`
- ReDoc: `http://localhost:8000/api/schema/redoc/`
- Schema: `http://localhost:8000/api/schema/`

## 🏍️ Rider System

### Rider Profile Fields

#### Personal Information
- `full_name`: Full name of the rider
- `phone_number`: Primary contact number
- `emergency_contact`: Emergency contact number

#### National Identity / Iqama
- `iqama_number`: 10-digit Iqama number (validated)
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
- `is_active`: Whether rider is active
- `is_available`: Whether rider is available for new orders
- `current_latitude`: Current GPS latitude
- `current_longitude`: Current GPS longitude

#### Statistics
- `total_deliveries`: Total completed deliveries
- `rating`: Average customer rating

### Document Types

Riders can upload the following documents:
- `iqama_front`: Iqama front side
- `iqama_back`: Iqama back side
- `license_front`: Driving license front
- `license_back`: Driving license back
- `istimara_front`: Vehicle registration (Istimara) front
- `istimara_back`: Vehicle registration (Istimara) back
- `insurance`: Insurance card/image

### Rider Approval Workflow

1. **Registration**: Rider registers → Review created with `draft` status
2. **Profile Completion**: Rider fills in all required information
3. **Document Upload**: Rider uploads required documents
4. **Submission**: Rider submits profile for review → Status changes to `pending`
5. **Admin Review**: Admin reviews profile and documents
6. **Approval/Rejection**: Admin approves or rejects with reason
7. **Active**: If approved, rider can accept orders

### GET Profile Response

The `GET /api/riders/profile/` endpoint returns:
```json
{
  "success": true,
  "data": {
    "id": 1,
    "username": "rider_username",
    "email": "rider@example.com",
    "is_phone_verified": true,
    "is_approved": true,
    "review_status": "approved",
    "full_name": "Rider Full Name",
    "phone_number": "+966501234567",
    "iqama_number": "1234567890",
    "iqama_expiry_date": "2025-12-31",
    "license_number": "DL123456",
    "license_expiry_date": "2026-06-30",
    "license_type": "private",
    "vehicle_type": "motorcycle",
    "vehicle_plate_number_english": "ABC123",
    "vehicle_make": "Honda",
    "vehicle_model": "CBR600",
    "vehicle_year": 2020,
    "vehicle_color": "Red",
    "vehicle_registration_number": "IST123456",
    "insurance_provider": "Tawuniya",
    "insurance_policy_number": "POL123456",
    "documents": [
      {
        "id": 1,
        "document_type": "iqama_front",
        "document_url": "http://example.com/media/rider_documents/iqama_front.jpg",
        "is_verified": true,
        "verified_at": "2024-01-15T10:30:00Z"
      }
    ],
    "total_deliveries": 50,
    "rating": "4.85",
    "is_active": true,
    "is_available": true
  }
}
```

## 📦 Order Flow

### Fabric Only Orders
```
Customer creates order → Payment (paid) → Rider accepts → 
Rider picks fabric from tailor → Rider marks ready_for_delivery → 
Rider delivers → Order status: delivered
```

### Fabric with Stitching Orders
```
Customer creates order → Payment (paid) → Rider accepts → 
Rider goes to customer → Takes measurements → 
Order status: measuring → cutting → stitching → ready_for_delivery → 
Rider delivers → Order status: delivered
```

### Order Status Flow

**Fabric Only:**
1. `pending` → Customer creates order
2. `confirmed` → Tailor accepts order
3. `paid` → Payment completed (order available for rider)
4. Rider accepts → Order assigned to rider
5. `ready_for_delivery` → Rider picks fabric from tailor
6. `delivered` → Rider delivers to customer

**Fabric with Stitching:**
1. `pending` → Customer creates order
2. `confirmed` → Tailor accepts order
3. `paid` → Payment completed (order available for rider)
4. Rider accepts → Status changes to `measuring`
5. `measuring` → Rider goes to customer location
6. Rider adds measurements → Status changes to `cutting`
7. `cutting` → Tailor cuts fabric
8. `stitching` → Tailor stitches garment
9. `ready_for_delivery` → Order ready for delivery
10. `delivered` → Rider delivers to customer

## 🎛️ Admin Interface

### Access
- URL: `http://localhost:8000/admin/`
- Login with superuser credentials

### Features
- **Rider Profile Management**: View and manage all rider profiles
- **Document Verification**: Verify rider documents (Iqama, License, Istimara, Insurance)
- **Profile Review**: Approve/reject rider profiles
- **Order Management**: View and manage all orders
- **Advanced Filtering**: Filter by status, date, type, etc.
- **Bulk Actions**: Approve/reject multiple riders, verify documents, etc.

### Admin Sections

#### Rider Profile Admin
- View all rider information
- See approval status badge
- Search by name, phone, Iqama, license, vehicle plate
- Filter by status, vehicle type, etc.

#### Rider Document Admin
- View all uploaded documents
- Verify/unverify documents
- See document preview
- Track verification history

#### Rider Profile Review Admin
- List pending reviews
- Approve/reject riders
- Add rejection reasons
- Track review timeline

## 🗄️ Database Models

### Rider Models

#### RiderProfile
Main rider profile model with all personal, vehicle, and insurance information.

#### RiderProfileReview
Tracks the review and approval process:
- `review_status`: draft, pending, approved, rejected
- `submitted_at`: When profile was submitted
- `reviewed_at`: When admin reviewed
- `reviewed_by`: Admin who reviewed
- `rejection_reason`: Reason if rejected

#### RiderDocument
Stores uploaded documents:
- `document_type`: Type of document
- `document_image`: Image file
- `is_verified`: Verification status
- `verified_at`: Verification timestamp
- `verified_by`: Admin who verified

#### RiderOrderAssignment
Tracks rider assignments to orders:
- `status`: pending, accepted, in_progress, completed, cancelled
- `accepted_at`: When rider accepted
- `started_at`: When rider started
- `completed_at`: When delivery completed

### Order Model Updates
- `rider`: ForeignKey to User (assigned rider)
- `rider_measurements`: JSONField for measurements
- `measurement_taken_at`: DateTimeField for measurement timestamp

## 🔐 Security & Permissions

- **JWT Authentication**: All endpoints require JWT tokens
- **Role-Based Access**: Riders, Tailors, Customers have different permissions
- **Phone Verification**: Required for riders
- **Admin Approval**: Riders must be approved before accepting orders
- **Document Verification**: Documents verified by admin

## 📝 Validation Rules

### Iqama Number
- Must be exactly 10 digits
- Validated using RegexValidator

### IBAN (Removed)
- ~~Must start with "SA" followed by 22 digits~~
- Bank account fields have been removed from the system

### Required Fields for Submission
- `full_name`
- `iqama_number`
- `phone_number`
- `license_number`
- `vehicle_type`
- `vehicle_plate_number_english`
- `vehicle_registration_number`

## 🧪 Testing

Run tests:
```bash
python manage.py test
```

## 📄 License

[Your License Here]

## 👥 Contributors

[Your Team/Contributors]

## 📞 Support

For support, email [your-email] or create an issue in the repository.

---

**Note**: This is a production-ready system designed for digitizing the Saudi Thobe tailoring industry. All features follow professional standards and best practices.

