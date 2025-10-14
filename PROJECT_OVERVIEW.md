# Zthob Backend - Project Overview & API Documentation

## Project Summary
Zthob is a comprehensive tailoring platform that connects customers with tailors for fabric purchasing and custom tailoring services. The platform supports multiple user roles (Customer, Tailor, Admin, Rider) and provides a complete order management system with status tracking.

## System Architecture

### Core Models & Relationships

#### 1. User Management (accounts app)
- **CustomUser**: Extended Django user with roles (USER, TAILOR, ADMIN, RIDER)
- **PhoneVerification**: OTP-based phone verification system
- **BaseModel**: Abstract base with created_at, updated_at, created_by fields

#### 2. Customer Management (customers app)
- **CustomerProfile**: Customer-specific information (gender, DOB, loyalty points)
- **Address**: Customer addresses with GPS coordinates
- **FamilyMember**: Family members with measurements and relationships

#### 3. Tailor Management (tailors app)
- **TailorProfile**: Tailor business information (shop name, experience, working hours)
- **TailorProfileReview**: Admin review system for tailor profiles
- **ServiceArea**: Geographic areas served by tailors
- **TailorServiceArea**: Many-to-many relationship between tailors and service areas

#### 4. Catalog Management (tailors app)
- **FabricCategory**: Product categories (e.g., Fabric, Caps, Handkerchief)
- **FabricType**: Types of fabrics (Cotton, Silk, Wool)
- **FabricTag**: Searchable tags for fabrics
- **Fabric**: Individual fabric items with pricing and inventory
- **FabricImage**: Image gallery for fabrics with primary image support

#### 5. Order Management (orders app)
- **Order**: Main order entity with comprehensive status tracking
- **OrderItem**: Individual items within orders
- **OrderStatusHistory**: Audit trail for status changes

## API Endpoints Documentation

### 1. Authentication & User Management (`/api/accounts/`)

#### User Registration
- **POST** `/api/accounts/register/`
- **Purpose**: Register new users with role assignment
- **Flow**: Create user → Generate JWT tokens → Return user data + tokens

#### User Login
- **POST** `/api/accounts/login/`
- **Purpose**: Authenticate users (supports username/email/phone)
- **Flow**: Validate credentials → Generate JWT tokens → Return tokens

#### User Profile
- **GET** `/api/accounts/profile/` - Get user profile
- **PUT** `/api/accounts/profile/` - Update user profile
- **POST** `/api/accounts/change-password/` - Change password

### 2. Customer APIs (`/api/customers/`)

#### Customer Profile Management
- **GET** `/api/customers/customerprofile/` - Get customer profile
- **PUT** `/api/customers/customerprofile/` - Update customer profile

#### Address Management
- **GET** `/api/customers/addresses/` - List customer addresses
- **POST** `/api/customers/addresses/create/` - Create new address
- **GET** `/api/customers/addresses/{id}/` - Get address details
- **PUT** `/api/customers/addresses/{id}/` - Update address
- **DELETE** `/api/customers/addresses/{id}/` - Delete address

#### Family Member Management
- **GET** `/api/customers/family/` - List family members
- **POST** `/api/customers/family/` - Add family member
- **GET** `/api/customers/family/{id}/` - Get family member details
- **PUT** `/api/customers/family/{id}/` - Update family member
- **DELETE** `/api/customers/family/{id}/` - Delete family member

#### Fabric Catalog
- **GET** `/api/customers/allfabrics/` - Browse all available fabrics

#### Phone Verification
- **POST** `/api/customers/phone/send-otp/` - Send OTP to phone
- **POST** `/api/customers/phone/verify-otp/` - Verify OTP code

### 3. Tailor APIs (`/api/tailors/`)

#### Profile Management
- **GET** `/api/tailors/profile/` - Get tailor profile
- **PUT** `/api/tailors/profile/` - Update tailor profile
- **POST** `/api/tailors/profile/submit/` - Submit profile for review
- **GET** `/api/tailors/profile/status/` - Check review status

#### Fabric Management
- **GET** `/api/tailors/fabrics/` - List tailor's fabrics
- **POST** `/api/tailors/fabrics/` - Create new fabric
- **GET** `/api/tailors/fabrics/{id}/` - Get fabric details
- **PUT** `/api/tailors/fabrics/{id}/` - Update fabric
- **PATCH** `/api/tailors/fabrics/{id}/` - Partial update fabric
- **DELETE** `/api/tailors/fabrics/{id}/` - Delete fabric

#### Fabric Metadata Management
- **GET** `/api/tailors/fabric-type/` - List fabric types
- **POST** `/api/tailors/fabric-type/` - Create fabric type
- **GET** `/api/tailors/fabric-type/{id}/` - Get fabric type details
- **PUT** `/api/tailors/fabric-type/{id}/` - Update fabric type
- **DELETE** `/api/tailors/fabric-type/{id}/` - Delete fabric type

- **GET** `/api/tailors/fabric-tags/` - List fabric tags
- **POST** `/api/tailors/fabric-tags/` - Create fabric tag
- **GET** `/api/tailors/fabric-tags/{id}/` - Get fabric tag details
- **PUT** `/api/tailors/fabric-tags/{id}/` - Update fabric tag
- **DELETE** `/api/tailors/fabric-tags/{id}/` - Delete fabric tag

- **GET** `/api/tailors/category/` - List fabric categories
- **POST** `/api/tailors/category/` - Create fabric category
- **DELETE** `/api/tailors/category/{id}/` - Delete fabric category

#### Image Management
- **POST** `/api/tailors/images/{id}/set-primary/` - Set primary image
- **DELETE** `/api/tailors/images/{id}/delete/` - Delete image

#### Service Area Management
- **GET** `/api/tailors/service-areas/available/` - List available service areas
- **GET** `/api/tailors/service-areas/` - List tailor's service areas
- **POST** `/api/tailors/service-areas/` - Add service area
- **GET** `/api/tailors/service-areas/{id}/` - Get service area details
- **PUT** `/api/tailors/service-areas/{id}/` - Update service area
- **DELETE** `/api/tailors/service-areas/{id}/` - Remove service area

#### Admin Review System
- **GET** `/api/tailors/admin/profiles/review/` - List profiles for review
- **GET** `/api/tailors/admin/profiles/review/{id}/` - Get review details
- **PUT** `/api/tailors/admin/profiles/review/{id}/` - Approve/reject profile

### 4. Order Management (`/api/orders/`)

#### Order Operations
- **GET** `/api/orders/` - List all orders (with filtering)
- **POST** `/api/orders/create/` - Create new order
- **GET** `/api/orders/{id}/` - Get order details
- **PUT** `/api/orders/{id}/` - Update order
- **DELETE** `/api/orders/{id}/` - Delete order (pending only)

#### Order Status Management
- **PATCH** `/api/orders/{id}/status/` - Update order status
- **GET** `/api/orders/{id}/history/` - Get order status history

#### User-Specific Order Views
- **GET** `/api/orders/my-orders/` - Customer's orders
- **GET** `/api/orders/my-tailor-orders/` - Tailor's assigned orders

## Order Status Flow

### Order Types
1. **FABRIC_ONLY**: Purchase fabric/item without stitching
2. **FABRIC_WITH_STITCHING**: Purchase fabric + get it stitched

### Status Flows

#### Fabric Only Flow (All Categories)
```
pending → confirmed → ready_for_delivery → delivered
```

#### Fabric with Stitching Flow (Fabric Category Only)
```
pending → confirmed → measuring → cutting → stitching → ready_for_delivery → delivered
```

### Role-Based Permissions

#### Customer (USER)
- Can only cancel orders (pending → cancelled)
- Can only cancel when status is 'pending'
- Can view their own orders and history

#### Tailor (TAILOR)
- Can update all statuses except cancellation
- Can only update orders assigned to them
- Cannot cancel orders (only customers can cancel)

#### Admin (ADMIN)
- Full control over all orders
- Can approve/reject tailor profiles
- Can manage service areas

## Key Features Implemented

### 1. Multi-Role Authentication System
- JWT-based authentication
- Role-based access control
- Phone verification with OTP

### 2. Comprehensive Order Management
- Order creation with multiple items
- Status tracking with audit trail
- Role-based status update permissions
- Order history tracking

### 3. Tailor Profile & Review System
- Tailor profile creation and management
- Admin review workflow
- Service area management
- Profile approval/rejection system

### 4. Fabric Catalog System
- Multi-category fabric management
- Image gallery with primary image support
- Inventory tracking
- Search and filtering capabilities

### 5. Customer Management
- Customer profiles with loyalty points
- Address management with GPS coordinates
- Family member management with measurements
- Phone verification

### 6. Service Area Management
- Geographic service area definition
- Tailor-service area relationships
- Delivery fee and time estimation

## Technical Implementation

### Backend Stack
- **Framework**: Django 5.x with Django REST Framework
- **Database**: SQLite (development), PostgreSQL (production ready)
- **Authentication**: JWT tokens with SimpleJWT
- **API Documentation**: drf-spectacular (Swagger/OpenAPI)
- **File Storage**: Local file system with media handling
- **Image Processing**: Django ImageField with validation

### Key Technical Features
- **Modular Architecture**: Separate apps for different domains
- **Comprehensive Serializers**: Detailed data validation and transformation
- **Permission System**: Role-based access control
- **Audit Trail**: Order status history tracking
- **File Upload**: Multi-part form data handling for images
- **API Documentation**: Auto-generated Swagger documentation
- **Error Handling**: Consistent API response format

### Database Design
- **Normalized Structure**: Proper foreign key relationships
- **Audit Fields**: Created/updated timestamps and user tracking
- **Soft Delete**: User soft deletion capability
- **Indexes**: Optimized queries for performance
- **Constraints**: Data integrity enforcement

## What's Remaining to Implement

### 1. Payment Integration
- Payment gateway integration (Stripe, PayPal, etc.)
- Payment status tracking
- Refund processing
- Payment history

### 2. Notification System
- Email notifications for order status changes
- SMS notifications for important updates
- Push notifications for mobile apps
- In-app notification system

### 3. Advanced Search & Filtering
- Elasticsearch integration for fabric search
- Advanced filtering by price, category, location
- Recommendation engine
- Search analytics

### 4. Mobile App APIs
- Mobile-specific endpoints
- Push notification endpoints
- Offline sync capabilities
- Mobile-optimized responses

### 5. Analytics & Reporting
- Order analytics dashboard
- Tailor performance metrics
- Customer behavior analytics
- Revenue reporting

### 6. Delivery Management
- Rider assignment system
- Delivery tracking
- Route optimization
- Delivery confirmation

### 7. Review & Rating System
- Customer reviews for tailors
- Rating system
- Review moderation
- Quality metrics

### 8. Inventory Management
- Low stock alerts
- Automatic reordering
- Supplier management
- Cost tracking

### 9. Advanced Features
- Multi-language support
- Multi-currency support
- Advanced reporting
- Data export capabilities
- Backup and recovery system

## Deployment & Infrastructure

### Current Setup
- **Development**: Local Django development server
- **Database**: SQLite for development
- **Static Files**: Django static file serving
- **Media Files**: Local file system

### Production Ready Features
- **Gunicorn**: WSGI server configuration
- **Nginx**: Reverse proxy configuration
- **Environment Variables**: Production environment setup
- **Database**: PostgreSQL ready
- **Static Files**: Static file collection and serving
- **Logging**: Comprehensive logging system

### Deployment Scripts
- **deploy.sh**: Automated deployment script
- **gunicorn.conf.py**: Gunicorn configuration
- **nginx.conf**: Nginx configuration
- **Environment templates**: Production environment setup

## API Documentation Access

The project includes comprehensive API documentation:
- **Swagger UI**: `/api/schema/swagger-ui/`
- **ReDoc**: `/api/schema/redoc/`
- **OpenAPI Schema**: `/api/schema/`

## Conclusion

The Zthob backend is a well-structured, comprehensive platform that provides:
- Complete user management with role-based access
- Full order lifecycle management
- Tailor profile and review system
- Fabric catalog with image management
- Customer management with family support
- Service area management
- Comprehensive API documentation

The system is production-ready with proper authentication, permissions, error handling, and deployment configurations. The remaining features focus on enhancing user experience, adding payment processing, and implementing advanced analytics and reporting capabilities.
