# Tailor Employee Permission Audit

## Date

2026-06-10

## Scope

Audit of employee access behavior for tailor-side endpoints under `/api/tailors/*`.

This review focuses on:

- whether active employee access resolves to the correct owner shop
- whether endpoint access is tied to the correct employee permission
- where access is still broad/basic shop access
- where behavior may still need a product decision

## Current Shared Rules

### Shared employee/shop resolution

Current backend now resolves employee shop context by prioritizing:

1. active `tailor_employee`
2. owner `tailor_profile`

This prevents employee stub tailor profiles from hijacking owner-shop access.

### Current employee permission flags

- `can_manage_orders`
- `can_manage_catalog`
- `can_view_analytics`
- `can_manage_employees`
- `can_manage_pos`

## Audit Summary

### Good: explicitly permission-gated

These areas are now mapped to employee permission flags:

| Area | Endpoints | Required employee permission |
|---|---|---|
| Dashboard home | `/tailors/home/` | `can_manage_orders` |
| Orders | `/tailors/orders/<id>/accept/`, `/update-status/`, `/measurements/`, `/download-pdf/` | `can_manage_orders` |
| Analytics | `/tailors/analytics/` | `can_view_analytics` |
| POS | `/tailors/pos/customers/`, `/pos/customers/create/`, `/pos/customers/<id>/orders/`, `/pos/customers/<id>/orders/<id>/` | `can_manage_pos` |
| Employees | `/tailors/employees/`, `/tailors/employees/<id>/` | `can_manage_employees` |
| Fabric create/update/delete | `/tailors/fabrics/` `POST`, `/tailors/fabrics/<id>/` `PUT/PATCH/DELETE` | `can_manage_catalog` |
| Fabric image actions | set primary, delete, add, update image | `can_manage_catalog` |

### Basic shop access only

These currently behave more like general staff shop access and are not tied to a dedicated employee permission flag:

| Area | Endpoints | Current behavior |
|---|---|---|
| Tailor profile read | `/tailors/profile/` `GET` | active employee can access owner shop profile |
| Tailor profile update | `/tailors/profile/` `PUT/PATCH` | active employee can update owner shop profile |
| Tailor profile submit | `/tailors/profile/submit/` | active employee can submit owner shop profile |
| Tailor profile status | `/tailors/profile/status/` | active employee can view profile review status |
| Shop on/off | `/tailors/shop/status/` | active employee can toggle shop status |

### Public or non-employee-scoped

These are not part of employee permission control:

| Area | Endpoints | Notes |
|---|---|---|
| Tailor config | `/tailors/config/` | currently `AllowAny` |
| Fabric type | `/tailors/fabric-type/*` | currently `AllowAny` |
| Fabric tags | `/tailors/fabric-tags/*` | currently `AllowAny` |
| Fabric categories read | `/tailors/category/`, `/tailors/category/<id>/` `GET` | public read |
| Fabric countries read | `/tailors/fabric-countries/` | public read |
| Admin review/service-area admin routes | `/tailors/admin/...` | admin-only |
| Service areas available | `/tailors/service-areas/available/` | public |
| Rating endpoints | customer-facing, not staff permission controlled |

### Not aligned for employee shop access

These are still using owner-only `IsTailor` or `request.user`-bound address behavior and are not currently employee-aware:

| Area | Endpoints | Current risk |
|---|---|---|
| Tailor address read | `/tailors/address/` | employee likely reads their own account address, not owner shop address |
| Tailor address create/update | `/tailors/address/manage/` | employee not scoped to owner shop address |
| Tailor address delete | `/tailors/address/delete/` | employee not scoped to owner shop address |

## Key Findings

### 1. The largest resolved issue

Employee users with role `TAILOR` could have a stub `TailorProfile`, which previously caused:

- wrong shop profile
- wrong fabric list
- wrong resource ownership checks

This is now resolved by prioritizing active `tailor_employee` context.

### 2. Home API now matches order permission

The dashboard home is order-centric, so tying it to `can_manage_orders` is correct and consistent.

### 3. Catalog image actions were a real permission gap

Those endpoints were previously owner-only by `request.user` check, which blocked valid employees even when catalog permission was enabled.

### 4. Profile/shop management is still broad

Right now, any active employee who has staff access can:

- update shop profile
- submit profile for review
- toggle shop open/closed

This may or may not be desired.

### 5. Address endpoints are still not employee-safe

They are still tied to `request.user` and `IsTailor`, not shop-staff shop context.

That means:

- employee may not access them correctly
- if employee does, it may target their own account’s addresses instead of the owner shop

## Recommended Permission Model

### Keep as-is

These are already aligned:

- `can_manage_orders`
- `can_manage_catalog`
- `can_manage_pos`
- `can_view_analytics`
- `can_manage_employees`

### Add new permission flags if you want stricter staff control

Suggested new flags:

- `can_manage_shop_profile`
- `can_manage_shop_status`
- `can_manage_shop_address`

If you add those, map them to:

| Suggested permission | Endpoints |
|---|---|
| `can_manage_shop_profile` | `/tailors/profile/` `PUT/PATCH`, `/profile/submit/`, `/profile/status/` |
| `can_manage_shop_status` | `/tailors/shop/status/` |
| `can_manage_shop_address` | `/tailors/address/`, `/address/manage/`, `/address/delete/` |

## Recommended Next Fixes

### High priority

1. Make tailor address endpoints employee-aware and resolve through owner shop context.
2. Decide whether employee profile edit/submit/status/shop-toggle should remain broad or require dedicated permissions.

### Medium priority

3. Review `TailorConfigView` being `AllowAny`. That may be intentional, but it is not a staff-protected route.
4. Review `fabric-type` and `fabric-tags` routes being `AllowAny` if they are truly meant to be public/mutable.

## Risk Assessment

### Low risk after current fixes

- order management
- dashboard home access
- analytics
- POS
- employee management
- fabric CRUD and fabric image management

### Medium risk / business decision needed

- shop profile edit flows
- shop open/close toggle

### Higher risk remaining mismatch

- tailor address endpoints

## QA Checklist

Use one owner and one employee account:

1. Enable only `can_manage_orders`
2. Verify employee can access `/tailors/home/`
3. Verify employee can accept/update orders
4. Verify employee cannot access `/tailors/employees/`
5. Enable only `can_manage_catalog`
6. Verify employee can access `/tailors/fabrics/`
7. Verify employee can modify fabric images
8. Disable `can_manage_catalog`
9. Verify catalog mutation endpoints return `403`
10. Check `/tailors/profile/` and `/tailors/shop/status/` behavior and confirm whether that broad access is desired
11. Check `/tailors/address/*` and confirm whether employee behavior is correct for your product requirements

## Final Conclusion

The main employee permission model is now much safer and more consistent for:

- orders
- dashboard
- catalog
- POS
- analytics
- employee management

The main unresolved edge area is shop-management behavior outside those flags, especially:

- tailor address
- profile edit/submit/status
- shop on/off toggle
