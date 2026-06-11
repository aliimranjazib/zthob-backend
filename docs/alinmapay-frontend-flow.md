# Alinma Pay Frontend Flow

This document explains how frontend should integrate with the current backend checkout flow for:

- Alinma hosted online payment
- COD / pay later

Important rule:

- For Alinma online payment, frontend must **not** call `POST /api/orders/checkout/create-order/`
- For COD / pay later, frontend **should** call `POST /api/orders/checkout/create-order/`

## Base URL

Current backend base URL:

```text
https://app.mgask.net
```

## Decision Table

| Payment case | Frontend flow | Open payment page | Call create-order API | Order created by |
|---|---|---|---|---|
| COD / pay later | checkout -> create-order | No | Yes | Frontend-triggered backend flow |
| Credit card `full` | checkout -> initiate-payment -> poll | Yes | No | Alinma callback |
| Credit card `advance_50` | checkout -> initiate-payment -> poll | Yes | No | Alinma callback |
| Credit card `advance_30` | checkout -> initiate-payment -> poll | Yes | No | Alinma callback |

## Checkout Status Meaning

Current checkout statuses:

- `active`: checkout draft created, payment not started yet
- `payment_initiated`: payment URL created, waiting for gateway confirmation
- `order_created`: payment success and order created
- `payment_failed`: payment failed
- `expired`: checkout expired

## Full Flow

### 1. Create checkout draft

Endpoint:

```text
POST /api/orders/checkout/
```

Example curl:

```bash
curl -X POST "https://app.mgask.net/api/orders/checkout/" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "tailor": 12,
    "order_type": "fabric_only",
    "service_mode": "home_delivery",
    "payment_method": "credit_card",
    "delivery_address": 5,
    "items": [
      {
        "fabric": 44,
        "quantity": 1,
        "measurements": {}
      }
    ]
  }'
```

Example response:

```json
{
  "success": true,
  "message": "Checkout created successfully",
  "data": {
    "bookingUniqueKey": "chk_abcd1234efgh5678ijkl9012",
    "status": "active",
    "pricing_summary": {
      "subtotal": "100.00",
      "stitching_price": "0.00",
      "tax_amount": "0.00",
      "delivery_fee": "0.00",
      "system_fee": "0.00",
      "express_fee": "0.00",
      "total_amount": "100.00",
      "items_count": 1,
      "payment_options": [
        {
          "key": "full",
          "label": "Pay Full Amount",
          "payment_plan": "full",
          "pay_now_amount": "100.00",
          "pay_later_amount": "0.00",
          "payment_status_after_order": "paid"
        },
        {
          "key": "advance_50",
          "label": "Pay 50% Advance",
          "payment_plan": "partial",
          "pay_now_amount": "50.00",
          "pay_later_amount": "50.00",
          "payment_status_after_order": "partially_paid"
        },
        {
          "key": "pay_later",
          "label": "Cash / Pay Later",
          "payment_plan": "pay_later",
          "pay_now_amount": "100.00",
          "pay_later_amount": "100.00",
          "payment_status_after_order": "pending"
        }
      ]
    },
    "expires_at": "2026-06-11T12:30:00Z",
    "payment_method": null,
    "payment_plan": null,
    "payment_option": null,
    "payment_reference": null,
    "order_id": null
  }
}
```

Frontend should save:

- `bookingUniqueKey`
- available `payment_options`
- `expires_at`

## Alinma Online Payment Flow

Use this flow only for:

- `full`
- `advance_50`
- `advance_30`

### 2. Initiate payment

Endpoint:

```text
POST /api/orders/checkout/initiate-payment/
```

Example curl:

```bash
curl -X POST "https://app.mgask.net/api/orders/checkout/initiate-payment/" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "bookingUniqueKey": "chk_abcd1234efgh5678ijkl9012",
    "payment_option": "full"
  }'
```

Example response:

```json
{
  "success": true,
  "message": "Alinma payment initiated successfully",
  "data": {
    "bookingUniqueKey": "chk_abcd1234efgh5678ijkl9012",
    "payment_option": "full",
    "gateway_transaction_id": "2610414541753672882",
    "payment_url": "https://pg.alinmapay.com.sa/SB_Transactions/direct.htm?paymentId=2610414541753672882",
    "amount": "100.00",
    "currency": "SAR",
    "status": "initiated"
  }
}
```

Frontend should:

- open `payment_url`
- use in-app webview or external browser
- do not render card fields inside app

### 3. Payment UI seen by customer

Customer enters payment details on Alinma hosted page, not inside your app.

That means:

- card number UI is from Alinma
- expiry and CVV UI is from Alinma
- 3DS / OTP / bank redirect is from Alinma

Frontend responsibility:

- just open the `payment_url`
- when page closes or app resumes, start polling checkout status

### 4. Poll checkout status

Endpoint:

```text
GET /api/orders/checkout/{bookingUniqueKey}/
```

Example curl:

```bash
curl -X GET "https://app.mgask.net/api/orders/checkout/chk_abcd1234efgh5678ijkl9012/" \
  -H "Authorization: Bearer <TOKEN>"
```

Example response while waiting:

```json
{
  "success": true,
  "message": "Checkout status retrieved successfully",
  "data": {
    "bookingUniqueKey": "chk_abcd1234efgh5678ijkl9012",
    "status": "payment_initiated",
    "pricing_summary": {
      "total_amount": "100.00"
    },
    "expires_at": "2026-06-11T12:30:00Z",
    "payment_method": "credit_card",
    "payment_plan": null,
    "payment_option": "full",
    "payment_reference": null,
    "order_id": null
  }
}
```

Example response after success:

```json
{
  "success": true,
  "message": "Checkout status retrieved successfully",
  "data": {
    "bookingUniqueKey": "chk_abcd1234efgh5678ijkl9012",
    "status": "order_created",
    "pricing_summary": {
      "total_amount": "100.00"
    },
    "expires_at": "2026-06-11T12:30:00Z",
    "payment_method": "credit_card",
    "payment_plan": "full",
    "payment_option": "full",
    "payment_reference": "2610414541753672882",
    "order_id": 987
  }
}
```

Example response after failure:

```json
{
  "success": true,
  "message": "Checkout status retrieved successfully",
  "data": {
    "bookingUniqueKey": "chk_abcd1234efgh5678ijkl9012",
    "status": "payment_failed",
    "pricing_summary": {
      "total_amount": "100.00"
    },
    "expires_at": "2026-06-11T12:30:00Z",
    "payment_method": "credit_card",
    "payment_plan": null,
    "payment_option": "full",
    "payment_reference": "2610414541753672882",
    "order_id": null
  }
}
```

Frontend polling behavior:

- start polling after payment page closes or app becomes active again
- poll every `2-3` seconds
- stop when status becomes:
  - `order_created`
  - `payment_failed`
  - `expired`

Frontend action by status:

- `payment_initiated`: show "Waiting for payment confirmation"
- `order_created`: navigate to order success/details using `order_id`
- `payment_failed`: show payment failed and allow retry
- `expired`: ask user to create checkout again

Important:

- For Alinma payment flow, frontend must **not** call `POST /api/orders/checkout/create-order/`
- backend callback creates the order automatically

## COD / Pay Later Flow

Use this flow only for:

- `pay_later`

### 2. Create order directly

Endpoint:

```text
POST /api/orders/checkout/create-order/
```

Example curl:

```bash
curl -X POST "https://app.mgask.net/api/orders/checkout/create-order/" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "bookingUniqueKey": "chk_abcd1234efgh5678ijkl9012",
    "payment_method": "cod"
  }'
```

Example response:

```json
{
  "success": true,
  "message": "Order created successfully from checkout",
  "data": {
    "id": 987,
    "order_number": "ORD-20260611-0001",
    "payment_method": "cod",
    "payment_status": "pending"
  }
}
```

Frontend should:

- call create-order directly
- no payment page
- navigate to order success/details after response

## Frontend State Machine

### Online payment

1. Create checkout
2. Show payment options
3. User selects `full` or `advance_50` or `advance_30`
4. Call `initiate-payment`
5. Open `payment_url`
6. Wait for app resume / payment page close
7. Poll checkout status
8. If `order_created`, open order success/details
9. If `payment_failed`, show retry

### COD

1. Create checkout
2. User selects `pay_later`
3. Call `create-order` with `payment_method=cod`
4. Open order success/details

## Apple Pay

Current backend phase is hosted payment page only.

What this means:

- frontend does not have separate Apple Pay API right now
- if Alinma merchant account and hosted page support Apple Pay, it may appear on the hosted payment page itself
- frontend flow stays exactly the same:
  - call `initiate-payment`
  - open `payment_url`
  - Alinma page may show Apple Pay on supported device/browser

So for now:

- no separate frontend Apple Pay implementation
- Apple Pay, if enabled by Alinma, is handled by Alinma hosted page UI

## Backend Callback

Frontend does not call this directly:

```text
POST /api/orders/checkout/alinma/callback/
```

This endpoint is called by Alinma gateway.

## Main Rule Summary

- Online payment:
  - call `checkout`
  - call `initiate-payment`
  - open `payment_url`
  - poll checkout status
  - do **not** call `create-order`

- COD / pay later:
  - call `checkout`
  - call `create-order`

