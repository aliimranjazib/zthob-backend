# Measurement Fee Plan

## Goal

Add a tailor-controlled measurement fee that is charged once per order when the customer needs home measurement service. The fee must be visible in checkout/pricing summary, stored on the order, and credited to the measurement rider wallet.

This is a money-flow change. It must be implemented with stored order snapshots and finance idempotency so delivery rider earnings and measurement rider earnings cannot block each other.

## Current Code Findings

- `OrderCalculationService.calculate_all_totals()` currently returns:
  - `subtotal`
  - `stitching_price`
  - `tax_amount`
  - `delivery_fee`
  - `system_fee`
  - `express_fee`
  - `total_amount`
- `measurement_service` orders currently force all pricing to zero after creation.
- Checkout already builds a pricing snapshot before order creation through `CheckoutCreateOrderSerializer.get_checkout_pricing_snapshot()`.
- Order creation recalculates totals and stores them directly on `Order`.
- Customer/tailor/rider order detail pricing summaries do not currently include `measurement_fee`.
- Rider wallet earning currently uses only `delivery_fee`.
- Rider wallet duplicate protection is currently per order:
  - `RiderWalletTransaction.objects.filter(order=order, transaction_type='credit').exists()`
  - This is not enough for the new flow because one order can now have both a measurement rider earning and a delivery rider earning.

## Recommended Data Model

### TailorProfile

Add a configurable default measurement fee:

```text
measurement_fee DecimalField(max_digits=10, decimal_places=2, default=0.00)
```

This is the fee the tailor controls.

### Order

Add an order-level snapshot:

```text
measurement_fee DecimalField(max_digits=10, decimal_places=2, default=0.00)
```

The order must store the fee used at checkout time. If the tailor changes their fee later, old orders should not change.

### RiderWalletTransaction

Add an earning type:

```text
earning_type choices:
- delivery
- measurement
```

Recommended guard:

```text
Only one credit transaction per wallet + order + earning_type.
```

This allows:

- measurement rider gets `measurement_fee`
- delivery rider gets `delivery_fee`
- same rider doing both gets two separate transactions
- duplicate signals do not double-credit either fee

## New Tailor API

### Add or Update Measurement Fee

```http
PATCH /api/tailors/measurement-fee/
Authorization: Bearer <tailor_token>
Content-Type: application/json
```

Payload:

```json
{
  "measurement_fee": "25.00"
}
```

Response:

```json
{
  "success": true,
  "message": "Measurement fee updated successfully",
  "data": {
    "measurement_fee": "25.00",
    "currency": "SAR"
  },
  "errors": null
}
```

Validation:

- tailor auth required
- fee must be decimal
- fee must be `>= 0`
- store with two decimal places
- reject invalid strings, negative values, and values above the agreed max

Optional read support:

```http
GET /api/tailors/measurement-fee/
```

Response:

```json
{
  "success": true,
  "message": "Measurement fee retrieved successfully",
  "data": {
    "measurement_fee": "25.00",
    "currency": "SAR"
  },
  "errors": null
}
```

## Pricing Rule

Add measurement fee once per order, not per item.

Apply the fee only when all are true:

- `service_mode = home_delivery`
- order needs measurement from rider
- customer has at least one order item/person without measurements
- tailor has `measurement_fee > 0`

Do not apply the fee when:

- service mode is `walk_in`
- all checkout items already have measurements
- tailor measurement fee is `0`
- order does not need measurement

Suggested calculation:

```text
measurement_fee = tailor.tailor_profile.measurement_fee
```

Only once:

```text
total_amount =
  subtotal
  + stitching_price
  + tax_amount
  + delivery_fee
  + system_fee
  + express_fee
  + measurement_fee
```

Important: current tax calculation is on fabric subtotal only. The first implementation should keep this behavior unchanged unless business confirms VAT must also apply on service fees.

## Checkout API Impact

### Existing Endpoint

```http
POST /api/orders/checkout/
```

Pricing summary should add:

```json
{
  "pricing_summary": {
    "subtotal": "100.00",
    "stitching_price": "80.00",
    "tax_amount": "15.00",
    "delivery_fee": "20.00",
    "system_fee": "3.00",
    "express_fee": "0.00",
    "measurement_fee": "25.00",
    "total_amount": "243.00",
    "items_count": 3,
    "payment_options": []
  }
}
```

Even if `items_count` is `3`, `measurement_fee` must remain `25.00`, not `75.00`.

### Existing Endpoint

```http
POST /api/orders/checkout/create-order/
```

Created order should store the same `measurement_fee` from the checkout/order calculation.

The payment amount sent to Alinma must match:

```text
checkout.pricing_snapshot.total_amount
```

which now includes `measurement_fee`.

## Order API Impact

All order detail/list serializers that expose pricing summary should include:

```json
{
  "pricing_summary": {
    "measurement_fee": "25.00"
  }
}
```

Affected surfaces:

- customer order detail/list
- tailor order detail/list
- rider order detail/list if pricing summary is exposed there
- checkout status
- checkout create response

## Rider Finance Impact

### Measurement Rider Earning

When the measurement work is complete and the order is eligible for wallet credit, credit:

```text
order.measurement_rider -> order.measurement_fee
```

For now, measurement rider should receive only this fee.

### Delivery Rider Earning

Keep existing delivery earning behavior:

```text
order.delivery_rider or active delivery rider -> order.delivery_fee
```

Do not credit delivery fee to a measurement-only rider unless the same user is also the delivery rider.

### Finance Response

Rider transaction history should expose `earning_type`.

Example:

```json
{
  "id": 501,
  "transaction_type": "credit",
  "source": "order",
  "earning_type": "measurement",
  "amount": "25.00",
  "description": "Measurement earning for Order ORD-12345",
  "order": {
    "id": 91,
    "order_number": "ORD-12345",
    "status": "in_progress",
    "total_amount": "243.00"
  }
}
```

Delivery earning example:

```json
{
  "transaction_type": "credit",
  "source": "order",
  "earning_type": "delivery",
  "amount": "20.00"
}
```

## Credit Timing Recommendation

Recommended robust behavior:

1. Try to create measurement earning when rider records all measurements.
2. Only actually credit when payment rules allow it.
3. Also retry from existing order finance signal when the order becomes paid/final.
4. Use the unique earning guard so retries are safe.

This prevents unpaid orders from incorrectly increasing rider wallet balance while still making sure the rider gets paid once the order is payable.

If business wants immediate rider credit for COD orders, define COD as eligible explicitly.

## Measurement Service Orders

Current code forces `measurement_service` orders to zero and marks them paid/free.

Because the new product flow says the customer selects a tailor for measurement, decide one of these two rules before implementation:

### Option A: Keep Free Measurement

If `measurement_service` must stay free:

- `measurement_fee = 0`
- rider does not get a wallet earning from this order
- current free measurement logic remains mostly unchanged

### Option B: Paid Measurement Service

If tailor measurement fee should apply:

- `measurement_service` checkout total becomes `measurement_fee`
- do not force `total_amount = 0`
- free first measurement logic must be adjusted carefully
- payment options must be generated from `measurement_fee`

Recommended for now: apply measurement fee to stitching orders that need home measurement, and only change `measurement_service` if product confirms it is no longer free.

## Edge Cases To Verify

- One order with one item missing measurements: fee added once.
- One order with multiple items missing measurements: fee added once.
- One order with multiple family members missing measurements: fee added once.
- All items already have measurements: fee is `0`.
- Walk-in order missing measurements: fee is `0`.
- Tailor fee is `0`: fee is `0`.
- Tailor updates fee after checkout session is created: checkout snapshot remains unchanged.
- Tailor updates fee after order is created: order snapshot remains unchanged.
- Measurement rider and delivery rider are different: both wallet credits can exist.
- Same rider handles measurement and delivery: same wallet gets two transactions with different `earning_type`.
- Signal runs twice: no duplicate credits.
- Delivery rider earning must not be blocked by existing measurement earning.
- Measurement earning must not be blocked by existing delivery earning.
- Alinma amount verification must use total including `measurement_fee`.
- Partial payment options must calculate from total including `measurement_fee`.

## Required Tests

Backend tests should cover:

- tailor can update measurement fee
- non-tailor cannot update measurement fee
- negative fee is rejected
- checkout adds one measurement fee for one missing measurement item
- checkout adds one measurement fee for multiple missing measurement items
- checkout does not add fee when measurements are already present
- checkout does not add fee for walk-in
- order creation stores `measurement_fee`
- pricing summary includes `measurement_fee`
- payment options calculate from total including `measurement_fee`
- measurement rider wallet gets measurement earning once
- delivery rider wallet still gets delivery earning once
- same rider can receive both earning types
- finance transaction response includes `earning_type`

## Implementation Order

1. Add migrations for `TailorProfile.measurement_fee`, `Order.measurement_fee`, and `RiderWalletTransaction.earning_type`.
2. Add tailor measurement fee serializer and endpoint.
3. Add measurement fee calculation helper in `OrderCalculationService`.
4. Include `measurement_fee` in checkout pricing snapshot and order creation totals.
5. Include `measurement_fee` in order pricing summaries.
6. Update rider finance service to separate delivery earning and measurement earning.
7. Update rider finance serializer to return `earning_type`.
8. Add regression tests for calculation, checkout, order snapshot, and rider finance.
9. Run migrations and targeted test suite.

## Safe Rollout Notes

- Default all new fees to `0.00`, so existing orders and existing tailors do not change behavior immediately.
- Existing orders should not be recalculated.
- New checkout sessions after a tailor fee update should use the new fee.
- Existing checkout sessions should keep their stored pricing snapshot.
- No frontend hard break if `measurement_fee` is added as an extra pricing summary key.
- Frontend should display the new key in checkout summary once backend is ready.

## Implemented Backend Shape

- Tailor fee endpoint:
  - `GET /api/tailors/measurement-fee/`
  - `PATCH /api/tailors/measurement-fee/`
- Tailor profile response now includes `measurement_fee` for display.
- Checkout pricing summary now includes `measurement_fee`.
- Order pricing summaries now include `measurement_fee`.
- Rider finance transactions now include `earning_type`.
- Rider wallet credits are split into:
  - `earning_type = delivery` for `delivery_fee`
  - `earning_type = measurement` for `measurement_fee`
- Checkout order creation pins money fields from the checkout pricing snapshot so fee changes after checkout do not change the created order total.
