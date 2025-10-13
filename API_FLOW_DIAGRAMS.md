# API Flow Diagrams - Zthob Backend

## 1. User Registration & Authentication Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant A as Auth API
    participant D as Database
    participant J as JWT Service

    Note over C,J: User Registration Flow
    C->>A: POST /api/accounts/register/
    A->>D: Create CustomUser
    D-->>A: User Created
    A->>J: Generate JWT Tokens
    J-->>A: Access & Refresh Tokens
    A-->>C: User Data + Tokens

    Note over C,J: User Login Flow
    C->>A: POST /api/accounts/login/
    A->>D: Validate Credentials
    D-->>A: User Found
    A->>J: Generate JWT Tokens
    J-->>A: Access & Refresh Tokens
    A-->>C: Tokens
```

## 2. Order Creation & Management Flow

```mermaid
sequenceDiagram
    participant C as Customer
    participant O as Order API
    participant T as Tailor API
    participant D as Database

    Note over C,D: Order Creation Flow
    C->>O: POST /api/orders/create/
    O->>D: Create Order (status: pending)
    D-->>O: Order Created
    O-->>C: Order Details

    Note over C,D: Order Status Updates
    T->>O: PATCH /api/orders/{id}/status/
    O->>D: Update Order Status
    O->>D: Create Status History
    D-->>O: Status Updated
    O-->>T: Updated Order

    Note over C,D: Order Cancellation
    C->>O: PATCH /api/orders/{id}/status/ (cancelled)
    O->>D: Update Status to Cancelled
    D-->>O: Status Updated
    O-->>C: Order Cancelled
```

## 3. Tailor Profile & Review Flow

```mermaid
sequenceDiagram
    participant T as Tailor
    participant TP as Tailor Profile API
    participant A as Admin API
    participant D as Database

    Note over T,D: Profile Creation
    T->>TP: PUT /api/tailors/profile/
    TP->>D: Create/Update TailorProfile
    D-->>TP: Profile Saved
    TP-->>T: Profile Data

    Note over T,D: Profile Submission
    T->>TP: POST /api/tailors/profile/submit/
    TP->>D: Create TailorProfileReview (pending)
    D-->>TP: Review Created
    TP-->>T: Submission Confirmed

    Note over T,D: Admin Review
    A->>A: GET /api/tailors/admin/profiles/review/
    A->>A: PUT /api/tailors/admin/profiles/review/{id}/ (approve/reject)
    A->>D: Update Review Status
    D-->>A: Status Updated
    A-->>A: Review Complete
```

## 4. Fabric Management Flow

```mermaid
sequenceDiagram
    participant T as Tailor
    participant F as Fabric API
    participant D as Database
    participant S as Storage

    Note over T,S: Fabric Creation
    T->>F: POST /api/tailors/fabrics/
    F->>D: Create Fabric
    F->>S: Upload Images
    S-->>F: Images Stored
    F->>D: Create FabricImages
    D-->>F: Fabric Created
    F-->>T: Fabric Details

    Note over T,S: Image Management
    T->>F: POST /api/tailors/images/{id}/set-primary/
    F->>D: Update Primary Image
    D-->>F: Image Updated
    F-->>T: Updated Fabric

    T->>F: DELETE /api/tailors/images/{id}/delete/
    F->>D: Delete Image
    F->>S: Remove File
    D-->>F: Image Deleted
    F-->>T: Updated Fabric
```

## 5. Customer Management Flow

```mermaid
sequenceDiagram
    participant C as Customer
    participant CP as Customer API
    participant D as Database

    Note over C,D: Profile Management
    C->>CP: GET /api/customers/customerprofile/
    CP->>D: Get CustomerProfile
    D-->>CP: Profile Data
    CP-->>C: Profile Details

    C->>CP: PUT /api/customers/customerprofile/
    CP->>D: Update Profile
    D-->>CP: Profile Updated
    CP-->>C: Updated Profile

    Note over C,D: Address Management
    C->>CP: POST /api/customers/addresses/create/
    CP->>D: Create Address
    D-->>CP: Address Created
    CP-->>C: Address Details

    Note over C,D: Family Member Management
    C->>CP: POST /api/customers/family/
    CP->>D: Create FamilyMember
    D-->>CP: Member Created
    CP-->>C: Member Details
```

## 6. Phone Verification Flow

```mermaid
sequenceDiagram
    participant U as User
    participant PV as Phone Verification API
    participant S as SMS Service
    participant D as Database

    Note over U,D: OTP Generation
    U->>PV: POST /api/customers/phone/send-otp/
    PV->>D: Create PhoneVerification
    PV->>S: Send OTP SMS
    S-->>PV: SMS Sent
    PV-->>U: OTP Sent Confirmation

    Note over U,D: OTP Verification
    U->>PV: POST /api/customers/phone/verify-otp/
    PV->>D: Validate OTP
    D-->>PV: OTP Valid
    PV->>D: Mark Phone as Verified
    D-->>PV: Phone Verified
    PV-->>U: Verification Success
```

## 7. Service Area Management Flow

```mermaid
sequenceDiagram
    participant T as Tailor
    participant SA as Service Area API
    participant A as Admin
    participant D as Database

    Note over T,D: Service Area Assignment
    T->>SA: GET /api/tailors/service-areas/available/
    SA->>D: Get Available Areas
    D-->>SA: Areas List
    SA-->>T: Available Areas

    T->>SA: POST /api/tailors/service-areas/
    SA->>D: Create TailorServiceArea
    D-->>SA: Area Assigned
    SA-->>T: Area Added

    Note over A,D: Admin Management
    A->>SA: POST /api/tailors/admin/service-areas/
    SA->>D: Create ServiceArea
    D-->>SA: Area Created
    SA-->>A: Area Details
```

## 8. Order Status Flow Diagram

```mermaid
stateDiagram-v2
    [*] --> pending: Order Created

    state "Fabric Only Flow" as FO
    state "Fabric with Stitching Flow" as FWS

    pending --> confirmed: Tailor Confirms
    pending --> cancelled: Customer Cancels

    confirmed --> FO: Fabric Only Order
    confirmed --> FWS: Stitching Order

    state FO {
        confirmed --> ready_for_delivery: Ready
        ready_for_delivery --> delivered: Delivered
    }

    state FWS {
        confirmed --> measuring: Take Measurements
        measuring --> cutting: Cut Fabric
        cutting --> stitching: Sew Garment
        stitching --> ready_for_delivery: Ready
        ready_for_delivery --> delivered: Delivered
    }

    delivered --> [*]
    cancelled --> [*]

    note right of pending
        Only customers can cancel
        Only when status is pending
    end note

    note right of confirmed
        Tailors can update status
        Customers cannot cancel
    end note
```

## 9. System Architecture Overview

```mermaid
graph TB
    subgraph "Client Layer"
        WEB[Web App]
        MOBILE[Mobile App]
        ADMIN[Admin Panel]
    end

    subgraph "API Layer"
        AUTH[Authentication API]
        CUSTOMER[Customer API]
        TAILOR[Tailor API]
        ORDER[Order API]
        CORE[Core Services]
    end

    subgraph "Business Logic"
        USER_MGMT[User Management]
        ORDER_MGMT[Order Management]
        PROFILE_MGMT[Profile Management]
        CATALOG_MGMT[Catalog Management]
    end

    subgraph "Data Layer"
        DB[PostgreSQL Database]
        MEDIA[Media Storage]
        CACHE[Redis Cache]
    end

    subgraph "External Services"
        SMS[SMS Service]
        EMAIL[Email Service]
        PAYMENT[Payment Gateway]
    end

    WEB --> AUTH
    MOBILE --> CUSTOMER
    ADMIN --> TAILOR
    WEB --> ORDER

    AUTH --> USER_MGMT
    CUSTOMER --> PROFILE_MGMT
    TAILOR --> CATALOG_MGMT
    ORDER --> ORDER_MGMT

    USER_MGMT --> DB
    ORDER_MGMT --> DB
    PROFILE_MGMT --> DB
    CATALOG_MGMT --> DB

    CORE --> SMS
    CORE --> EMAIL
    ORDER_MGMT --> PAYMENT

    CATALOG_MGMT --> MEDIA
    PROFILE_MGMT --> MEDIA
```

## 10. Complete System Entity Relationship Diagram

```mermaid
erDiagram
    %% Core User Management
    CustomUser {
        int id PK
        string username
        string email
        string phone
        string role
        boolean is_active
        boolean phone_verified
        datetime created_at
    }
    
    PhoneVerification {
        int id PK
        int user_id FK
        string phone_number
        string otp_code
        boolean is_verified
        datetime expires_at
        datetime created_at
    }

    %% Customer Management
    CustomerProfile {
        int id PK
        int user_id FK
        string gender
        date date_of_birth
        int loyalty_points
        string tags
        int default_address_id FK
    }
    
    Address {
        int id PK
        int user_id FK
        string street
        string city
        string state_province
        string zip_code
        string country
        decimal latitude
        decimal longitude
        boolean is_default
    }
    
    FamilyMember {
        int id PK
        int user_id FK
        string name
        string gender
        string relationship
        json measurements
        int address_id FK
    }

    %% Tailor Management
    TailorProfile {
        int id PK
        int user_id FK
        string shop_name
        string contact_number
        int establishment_year
        int tailor_experience
        json working_hours
        string address
        boolean shop_status
        string shop_image
        datetime created_at
    }
    
    TailorProfileReview {
        int id PK
        int profile_id FK
        string review_status
        datetime submitted_at
        datetime reviewed_at
        int reviewed_by_id FK
        text rejection_reason
        json service_areas
    }

    %% Service Area Management
    ServiceArea {
        int id PK
        string name
        string city
        boolean is_active
        datetime created_at
    }
    
    TailorServiceArea {
        int id PK
        int tailor_id FK
        int service_area_id FK
        boolean is_primary
        decimal delivery_fee
        int estimated_delivery_days
    }

    %% Catalog Management
    FabricCategory {
        int id PK
        string name
        string slug
        boolean is_active
        datetime created_at
    }
    
    FabricType {
        int id PK
        string name
        string slug
        datetime created_at
    }
    
    FabricTag {
        int id PK
        string name
        string slug
        boolean is_active
        datetime created_at
    }
    
    Fabric {
        int id PK
        int tailor_id FK
        int fabric_type_id FK
        int category_id FK
        string name
        text description
        string sku
        decimal price
        int stock
        string seasons
        boolean is_active
        string fabric_image
        datetime created_at
    }
    
    FabricImage {
        int id PK
        int fabric_id FK
        string image
        boolean is_primary
        int order
        datetime created_at
    }

    %% Order Management
    Order {
        int id PK
        int customer_id FK
        int tailor_id FK
        string order_type
        string order_number
        string status
        decimal subtotal
        decimal tax_amount
        decimal delivery_fee
        decimal total_amount
        string payment_status
        string payment_method
        int family_member_id FK
        int delivery_address_id FK
        date estimated_delivery_date
        date actual_delivery_date
        text special_instructions
        text notes
        datetime created_at
    }
    
    OrderItem {
        int id PK
        int order_id FK
        int fabric_id FK
        int quantity
        decimal unit_price
        decimal total_price
        json measurements
        text custom_instructions
        boolean is_ready
        datetime created_at
    }
    
    OrderStatusHistory {
        int id PK
        int order_id FK
        string status
        string previous_status
        int changed_by_id FK
        text notes
        datetime created_at
    }

    %% Relationships
    CustomUser ||--o| CustomerProfile : "has profile"
    CustomUser ||--o| TailorProfile : "has profile"
    CustomUser ||--o{ Address : "owns"
    CustomUser ||--o{ FamilyMember : "has"
    CustomUser ||--o{ Order : "places"
    CustomUser ||--o{ Order : "assigned to"
    CustomUser ||--o{ PhoneVerification : "verifies"
    CustomUser ||--o{ OrderStatusHistory : "changes"

    CustomerProfile ||--o| Address : "default address"
    FamilyMember ||--o| Address : "lives at"

    TailorProfile ||--o| TailorProfileReview : "reviewed"
    TailorProfile ||--o{ Fabric : "owns"
    TailorProfile ||--o{ TailorServiceArea : "serves"
    TailorProfile ||--o{ Order : "handles"

    ServiceArea ||--o{ TailorServiceArea : "served by"

    FabricCategory ||--o{ Fabric : "contains"
    FabricType ||--o{ Fabric : "categorizes"
    FabricTag }o--o{ Fabric : "tags"
    Fabric ||--o{ FabricImage : "has images"
    Fabric ||--o{ OrderItem : "ordered as"

    Order ||--o{ OrderItem : "contains"
    Order ||--o{ OrderStatusHistory : "tracked by"
    Order }o--o| FamilyMember : "for member"
    Order }o--o| Address : "delivery address"

    OrderItem }o--|| Fabric : "is fabric"
```

## API Response Format

All APIs follow a consistent response format:

```json
{
    "success": true,
    "message": "Operation completed successfully",
    "data": {
        // Response data here
    },
    "errors": null
}
```

## Error Response Format

```json
{
    "success": false,
    "message": "Operation failed",
    "data": null,
    "errors": {
        "field_name": ["Error message"]
    }
}
```

## Authentication

All protected endpoints require JWT authentication:

```
Authorization: Bearer <access_token>
```

## Rate Limiting

- Phone verification: 5 requests per hour per user
- Login attempts: 10 attempts per hour per IP
- API calls: 1000 requests per hour per user

## File Upload

- Supported formats: JPG, JPEG, PNG
- Maximum file size: 10MB
- Multiple images supported for fabrics
- Primary image designation system
