# Owner App — API Guide

Base URL: **`/api/`** (or `/api/v1/`)

Auth header (after login): **`Authorization: Bearer <access_token>`**

---

## Response format

All APIs return the same shape:

```json
{
  "success": true,
  "message": "Description of result",
  "data": { },
  "errors": null
}
```

| HTTP | Meaning |
|------|---------|
| 200 | Success (existing user / read) |
| 201 | Created (new user / new resource) |
| 400 | Invalid request body |
| 403 | Not allowed (e.g. switch to someone else's shop) |
| 404 | Resource not found (or not yours) |

---

## App flows

### Flow 1 — Owner opens dashboard (first time)

Use this when the user picks **“Shop owner”** on the login screen.

```
1. POST /api/accounts/phone-login/          → send OTP
2. POST /api/accounts/owner/phone-verify/   → login + get tokens
3. Open owner dashboard (Shops / Staff / Reports tabs)
```

If `owned_shops` is empty → show **Create shop** first.  
If `can_enter_shop_work` is true → owner can open a shop for daily work.

---

### Flow 2 — Owner enters one shop to work (orders, POS, catalog)

Use this when the owner taps a shop to **work inside it** (same as old tailor app).

```
1. Already logged in (Flow 1)
2. POST /api/accounts/owner/switch-shop/   → pass shop_id
3. Save new access_token (JWT now has shop_id)
4. Call existing tailor APIs (orders, POS, etc.) — they auto-scope to that shop
```

No re-login needed. Only the token changes.

---

### Flow 3 — Staff member login

Staff uses the **same owner verify endpoint**, not a separate login API.

```
1. POST /api/accounts/phone-login/
2. POST /api/accounts/owner/phone-verify/
3. Read assigned_shops from tailor_context
4. POST /api/accounts/owner/switch-shop/   → pick assigned shop
5. access_mode becomes "employee" — use tailor APIs with limited permissions
```

---

### Flow 4 — Owner dashboard tabs (which API to call)

| Tab | APIs |
|-----|------|
| **Shops** | `GET/POST /tailors/owner/shops/` |
| **Staff** | `GET/POST /tailors/owner/staff/` + assignments |
| **Reports** | `GET /tailors/owner/reports/` |
| **All orders** | `GET /tailors/owner/orders/` |

---

# Authentication

---

## Send OTP

**What:** Sends a 4-digit code to the phone. First step for every phone login.

| | |
|---|---|
| **Method** | `POST` |
| **URL** | `/api/accounts/phone-login/` |
| **Auth** | None |

**Request:**
```json
{
  "phone": "0511111111"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "OTP sent successfully",
  "data": {
    "verification_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "phone": "0511111111",
    "otp_expires_at": "2026-09-02T10:05:00+00:00"
  }
}
```

**Note:** Save `verification_id` for the verify step.

---

## Owner login / register

**What:** Verifies OTP and logs the user into the **owner app**. Creates account if new. Returns JWT + owner navigation data.

| | |
|---|---|
| **Method** | `POST` |
| **URL** | `/api/accounts/owner/phone-verify/` |
| **Auth** | None |

**Do not use** `/api/accounts/phone-verify/` for the owner app — that one is for customer/legacy tailor apps.

**Request:**
```json
{
  "verification_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "otp_code": "1234",
  "name": "Ahmed Ali"
}
```

**Response (201 new user / 200 existing):**
```json
{
  "success": true,
  "message": "Registration and login successful",
  "data": {
    "tokens": {
      "access_token": "eyJhbGciOiJIUzI1NiIs...",
      "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
    },
    "user": {
      "id": 1,
      "phone": "0511111111",
      "first_name": "Ahmed",
      "last_name": "Ali",
      "role": "TAILOR"
    },
    "is_new_user": true,
    "tailor_context": {
      "is_owner": false,
      "is_employee": false,
      "shop_id": null,
      "roles": [],
      "permissions": {},

      "app_entry": "owner",
      "mode": "owner",
      "access_mode": "owner",
      "active_shop_id": null,
      "owned_shops": [],
      "assigned_shops": [],
      "can_enter_shop_work": false,
      "routing": {
        "initial_screen": "owner_dashboard"
      }
    }
  }
}
```

**How to use `tailor_context`:**

| Field | Use in app |
|-------|------------|
| `routing.initial_screen` | `"owner_dashboard"` → show owner tabs |
| `owned_shops` | Shops tab list (also available via shops API) |
| `assigned_shops` | Shops staff can switch to (staff users) |
| `can_enter_shop_work` | Show “enter shop” only if `true` |
| `active_shop_id` | Currently selected shop (null until switch-shop) |

---

## Switch active shop

**What:** Sets which shop the user is working in. Returns a **new token** with `shop_id` inside JWT. Use before opening orders/POS.

| | |
|---|---|
| **Method** | `POST` |
| **URL** | `/api/accounts/owner/switch-shop/` |
| **Auth** | Bearer token |

**Request:**
```json
{
  "shop_id": 12
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Shop session updated successfully",
  "data": {
    "tokens": {
      "access_token": "eyJ...",
      "refresh_token": "eyJ..."
    },
    "tailor_context": {
      "active_shop_id": 12,
      "shop_id": 12,
      "access_mode": "owner",
      "app_entry": "owner",
      "owned_shops": [
        {
          "id": 12,
          "shop_name": "Main Branch",
          "shop_status": true,
          "is_verified": false,
          "is_pinned": true
        }
      ],
      "assigned_shops": [],
      "routing": {
        "initial_screen": "shop_work"
      }
    }
  }
}
```

**After success:** Replace stored token. JWT payload includes:
```json
{
  "shop_id": 12,
  "access_mode": "owner",
  "app_entry": "owner"
}
```

**Errors:**
- `403` — user does not own this shop and is not assigned as staff
- `400` — missing or invalid `shop_id`

---

## Refresh auth context

**What:** Reloads user + `tailor_context` without sending OTP again. Use on app resume.

| | |
|---|---|
| **Method** | `GET` |
| **URL** | `/api/accounts/owner/context/` |
| **Auth** | Bearer token |

**Response (200):**
```json
{
  "success": true,
  "message": "Owner auth context fetched successfully",
  "data": {
    "user": { "id": 1, "phone": "0511111111", "role": "TAILOR" },
    "tailor_context": { "...same as login..." }
  }
}
```

---

# Shops

All shop APIs require **Bearer token** (logged-in owner).

---

## List my shops

**What:** Returns every shop owned by the logged-in user. Pinned shops appear first.

| | |
|---|---|
| **Method** | `GET` |
| **URL** | `/api/tailors/owner/shops/` |

**Response (200):**
```json
{
  "success": true,
  "message": "Owned shops retrieved successfully",
  "data": [
    {
      "id": 12,
      "shop_name": "Main Branch",
      "contact_number": "0511111111",
      "address": "Riyadh",
      "shop_status": true,
      "is_pinned": true,
      "is_verified": false,
      "shop_image": null,
      "shop_image_url": null,
      "working_hours": {},
      "establishment_year": null,
      "tailor_experience": null,
      "created_at": "2026-09-02T08:00:00Z",
      "updated_at": "2026-09-02T08:00:00Z"
    }
  ]
}
```

---

## Create shop

**What:** Adds a new shop under this owner. Owner can create many shops.

| | |
|---|---|
| **Method** | `POST` |
| **URL** | `/api/tailors/owner/shops/` |
| **Body** | JSON or `multipart/form-data` (if uploading `shop_image`) |

**Request:**
```json
{
  "shop_name": "Mall Branch",
  "address": "Jeddah",
  "contact_number": "0511111111",
  "is_pinned": true
}
```

**Response (201):** Same shop object as in list (single object in `data`).

**Required:** `shop_name` (non-empty)

---

## Get shop details

**What:** Returns one shop by ID (must be yours).

| | |
|---|---|
| **Method** | `GET` |
| **URL** | `/api/tailors/owner/shops/{shop_id}/` |

**Response (200):** Single shop object in `data`.

**Response (404):** Shop not found or not owned by you.

---

## Update shop

**What:** Updates shop fields (name, address, image, etc.).

| | |
|---|---|
| **Method** | `PATCH` |
| **URL** | `/api/tailors/owner/shops/{shop_id}/` |

**Request (send only fields to change):**
```json
{
  "shop_name": "Updated Name",
  "address": "New address"
}
```

**Response (200):** Updated shop object.

---

## Pin / unpin shop

**What:** Controls whether shop shows in owner quick-access list.

| | |
|---|---|
| **Method** | `PATCH` |
| **URL** | `/api/tailors/owner/shops/{shop_id}/pin/` |

**Request:**
```json
{
  "is_pinned": false
}
```

**Response (200):** Updated shop object.

---

# Staff

Manage employees across all your shops. One person can work at multiple shops with different permissions.

**Staff roles:** `manager`, `stitcher`, `cutter`, `receptionist`, `finisher`

**Staff permissions (send as list of strings):**

| Permission | Allows |
|------------|--------|
| `can_manage_orders` | Manage orders |
| `can_manage_catalog` | Fabrics / catalog |
| `can_view_analytics` | View analytics |
| `can_manage_employees` | Manage employees |
| `can_manage_pos` | Walk-in POS |
| `can_manage_shop_profile` | Edit shop profile |
| `can_manage_shop_status` | Open/close shop |
| `can_manage_shop_address` | Edit address |
| `can_stitch_orders` | Stitching jobs |

---

## List staff roster

**What:** All staff members you added, with their shop assignments.

| | |
|---|---|
| **Method** | `GET` |
| **URL** | `/api/tailors/owner/staff/` |

**Response (200):**
```json
{
  "success": true,
  "message": "Staff roster retrieved successfully",
  "data": [
    {
      "id": 1,
      "name": "Ahmed Ali",
      "phone": "0511111113",
      "is_active": true,
      "assignments": [
        {
          "id": 10,
          "shop_id": 12,
          "shop_name": "Main Branch",
          "roles": ["stitcher"],
          "permissions": {
            "can_stitch_orders": true,
            "can_manage_orders": false,
            "can_manage_catalog": false,
            "can_view_analytics": false,
            "can_manage_employees": false,
            "can_manage_pos": false,
            "can_manage_shop_profile": false,
            "can_manage_shop_status": false,
            "can_manage_shop_address": false
          },
          "is_active": true,
          "assigned_at": "2026-09-02T08:00:00Z",
          "updated_at": "2026-09-02T08:00:00Z"
        }
      ],
      "joined_at": "2026-09-02T08:00:00Z",
      "updated_at": "2026-09-02T08:00:00Z"
    }
  ]
}
```

---

## Add staff member

**What:** Adds a person to your roster. Optionally assigns them to a shop in the same request. Creates their user account if phone is new.

| | |
|---|---|
| **Method** | `POST` |
| **URL** | `/api/tailors/owner/staff/` |

**Request:**
```json
{
  "name": "Ahmed Ali",
  "phone": "0511111113",
  "roles": ["stitcher"],
  "permissions": ["can_stitch_orders"],
  "shop_id": 12,
  "is_active": true
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Display name |
| `phone` | Yes | Saudi phone (staff login phone) |
| `roles` | No | Default `[]` |
| `permissions` | No | Default `[]` |
| `shop_id` | No | If sent, creates shop assignment immediately |
| `is_active` | No | Default `true` |

**Response (201):** Staff member object (same shape as list item).

**Error (400):** Cannot add your own owner phone as staff.

---

## Get / update / remove staff member

| Action | Method | URL |
|--------|--------|-----|
| Get one | `GET` | `/api/tailors/owner/staff/{staff_id}/` |
| Update | `PATCH` | `/api/tailors/owner/staff/{staff_id}/` |
| Remove | `DELETE` | `/api/tailors/owner/staff/{staff_id}/` |

**PATCH request:**
```json
{
  "name": "Ahmed Ali Updated",
  "is_active": false
}
```

**DELETE response (200):**
```json
{
  "success": true,
  "message": "Staff member removed successfully",
  "data": null
}
```

---

## List / add shop assignment

**What:** Assign an existing roster member to another shop (or first shop if added without `shop_id`).

| | |
|---|---|
| **List** | `GET /api/tailors/owner/staff/{staff_id}/assignments/` |
| **Add** | `POST /api/tailors/owner/staff/{staff_id}/assignments/` |

**POST request:**
```json
{
  "shop_id": 15,
  "roles": ["manager"],
  "permissions": ["can_manage_orders", "can_manage_pos"],
  "is_active": true
}
```

**Response (201):**
```json
{
  "success": true,
  "message": "Staff assignment saved successfully",
  "data": {
    "id": 11,
    "shop_id": 15,
    "shop_name": "Mall Branch",
    "roles": ["manager"],
    "permissions": { "...": "..." },
    "is_active": true,
    "assigned_at": "2026-09-02T08:00:00Z",
    "updated_at": "2026-09-02T08:00:00Z"
  }
}
```

---

## Update / remove assignment

| Action | Method | URL |
|--------|--------|-----|
| Update roles/permissions | `PATCH` | `/api/tailors/owner/staff/{staff_id}/assignments/{assignment_id}/` |
| Unassign from shop | `DELETE` | `/api/tailors/owner/staff/{staff_id}/assignments/{assignment_id}/` |

**PATCH request:**
```json
{
  "roles": ["stitcher"],
  "permissions": ["can_stitch_orders", "can_manage_orders"],
  "is_active": true
}
```

---

# Orders & reports

---

## List orders (all my shops)

**What:** Owner dashboard view of orders across every owned shop. Optional filters.

| | |
|---|---|
| **Method** | `GET` |
| **URL** | `/api/tailors/owner/orders/` |

**Query parameters (all optional):**

| Param | Example | Filters by |
|-------|---------|------------|
| `shop_id` | `12` | One shop only |
| `status` | `confirmed` | Order status |
| `payment_status` | `paid` | Payment status |
| `service_mode` | `walk_in` | `walk_in` or `home_delivery` |
| `order_type` | `fabric_with_stitching` | Order type |

**Example:** `GET /api/tailors/owner/orders/?shop_id=12&status=confirmed`

**Response (200):**
```json
{
  "success": true,
  "message": "Owner orders retrieved successfully",
  "data": [
    {
      "id": 100,
      "order_number": "00300",
      "status": "confirmed",
      "payment_status": "paid",
      "service_mode": "walk_in",
      "order_type": "fabric_with_stitching",
      "customer_name": "Sara",
      "customer_phone": "0501234567",
      "tailor_name": "Main Branch",
      "total_amount": "250.00",
      "is_express": false,
      "created_at": "2026-09-02T08:00:00Z"
    }
  ]
}
```

---

## Get order detail

**What:** Full order details for owner dashboard.

| | |
|---|---|
| **Method** | `GET` |
| **URL** | `/api/tailors/owner/orders/{order_id}/` |

**Response (200):** Full order object (items, pricing, status, measurements, etc.).

**Response (404):** Order not in any of your shops.

---

## Owner reports

**What:** Summary for Reports tab — orders, revenue, walk-in sales per shop.

| | |
|---|---|
| **Method** | `GET` |
| **URL** | `/api/tailors/owner/reports/` |

**Query parameters:**

| Param | Default | Description |
|-------|---------|-------------|
| `shop_id` | all shops | Limit to one shop |
| `sales_period` | `this_month` | `today`, `yesterday`, `this_week`, `this_month`, `past_6_months` |

**Example:** `GET /api/tailors/owner/reports/?sales_period=this_month`

**Response (200):**
```json
{
  "success": true,
  "message": "Owner reports retrieved successfully",
  "data": {
    "generated_at": "2026-09-02T08:00:00+00:00",
    "filters": {
      "shop_id": null,
      "sales_period": "this_month"
    },
    "summary": {
      "shops_count": 2,
      "orders_total": 45,
      "orders_completed": 30,
      "orders_active": 10,
      "revenue_total": "12500.00",
      "status_breakdown": {
        "confirmed": 5,
        "collected": 30,
        "cancelled": 2
      }
    },
    "shops": [
      {
        "shop_id": 12,
        "shop_name": "Main Branch",
        "is_pinned": true,
        "orders": {
          "total": 25,
          "completed": 18,
          "active": 5
        },
        "revenue": {
          "total_collected": "8000.00"
        },
        "shop_sales": {
          "title": "Shop sales (Walk-in)",
          "disclaimer": "Collected at your shop. Not included in wallet balance.",
          "period": {
            "key": "this_month",
            "from": "2026-09-01",
            "to": "2026-09-30"
          },
          "orders_count": 12,
          "total_collected": "4500.00",
          "breakdown": {
            "subtotal": "3000.00",
            "stitching_price": "1200.00",
            "express_fee": "300.00"
          }
        }
      }
    ]
  }
}
```

---

# Shop work mode (existing tailor APIs)

After **switch-shop**, use these **existing** endpoints with the new token. They automatically filter by `shop_id` in JWT.

| What | Method | URL |
|------|--------|-----|
| My orders | `GET` | `/api/orders/tailor/my-orders/` |
| Available orders | `GET` | `/api/orders/tailor/available-orders/` |
| Order detail | `GET` | `/api/orders/tailor/{order_id}/` |
| Order history | `GET` | `/api/orders/tailor/history/` |
| Paid / COD orders | `GET` | `/api/orders/tailor/paid-orders/` |
| Analytics | `GET` | `/api/tailors/analytics/?days=30` |
| Walk-in sales | `GET` | `/api/finance/shop-sales/summary/` |
| POS customers | `GET` | `/api/tailors/pos/customers/` |

**Flow:**
```
switch-shop (shop_id=12) → save token → GET /api/orders/tailor/my-orders/
→ only Shop 12 orders returned
```

---

# Endpoint quick reference

| # | Method | Endpoint | Purpose |
|---|--------|----------|---------|
| 1 | POST | `/api/accounts/phone-login/` | Send OTP |
| 2 | POST | `/api/accounts/owner/phone-verify/` | Owner login |
| 3 | POST | `/api/accounts/owner/switch-shop/` | Enter shop session |
| 4 | GET | `/api/accounts/owner/context/` | Refresh context |
| 5 | GET | `/api/tailors/owner/shops/` | List shops |
| 6 | POST | `/api/tailors/owner/shops/` | Create shop |
| 7 | GET | `/api/tailors/owner/shops/{id}/` | Shop detail |
| 8 | PATCH | `/api/tailors/owner/shops/{id}/` | Update shop |
| 9 | PATCH | `/api/tailors/owner/shops/{id}/pin/` | Pin/unpin |
| 10 | GET | `/api/tailors/owner/staff/` | List staff |
| 11 | POST | `/api/tailors/owner/staff/` | Add staff |
| 12 | GET/PATCH/DELETE | `/api/tailors/owner/staff/{id}/` | Staff detail |
| 13 | GET/POST | `/api/tailors/owner/staff/{id}/assignments/` | Assignments |
| 14 | PATCH/DELETE | `/api/tailors/owner/staff/{id}/assignments/{aid}/` | Edit assignment |
| 15 | GET | `/api/tailors/owner/orders/` | All orders |
| 16 | GET | `/api/tailors/owner/orders/{id}/` | Order detail |
| 17 | GET | `/api/tailors/owner/reports/` | Dashboard reports |

---

# Important notes

1. **Owner app must use** `/owner/phone-verify/` — not the generic phone verify.
2. **No separate OWNER role** — everyone uses `role: TAILOR`; owner vs staff is determined by `tailor_context` and JWT claims.
3. **After switch-shop**, always save the new `access_token`.
4. **Owner does not need** a staff record to work in their own shop — only `switch-shop` is required.
5. **Legacy tailor app** is unchanged — it still uses `/api/accounts/phone-verify/` without owner fields.
