# Measurement Fee Frontend Integration Guide

## Summary

Backend now supports a tailor-controlled one-time `measurement_fee`.

This fee is used when a customer creates a home-delivery order that needs rider measurement. The customer should see this fee in checkout and order pricing summaries. The frontend must not calculate or send this fee manually; backend calculates it from the selected tailor profile.

## New Tailor API

### Get Current Measurement Fee

```http
GET /api/tailors/measurement-fee/
Authorization: Bearer <tailor_token>
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

### Update Measurement Fee

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

Success response:

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

- `measurement_fee` must be a positive or zero decimal.
- Negative values are rejected.
- Use string decimal values like `"25.00"`.

Example invalid response:

```json
{
  "success": false,
  "message": "Validation failed",
  "data": null,
  "errors": {
    "measurement_fee": [
      "Ensure this value is greater than or equal to 0.00."
    ]
  }
}
```

## Tailor Profile Response Change

Tailor profile response now includes:

```json
{
  "measurement_fee": "25.00"
}
```

Use this for display only. For updating the fee, use:

```http
PATCH /api/tailors/measurement-fee/
```

## Checkout Pricing Response Change

Checkout pricing summary now includes `measurement_fee`.

Affected endpoint:

```http
POST /api/orders/checkout/
```

Example response fragment:

```json
{
  "pricing_summary": {
    "subtotal": "200.00",
    "stitching_price": "0.00",
    "tax_amount": "30.00",
    "delivery_fee": "20.00",
    "system_fee": "3.00",
    "express_fee": "0.00",
    "measurement_fee": "25.00",
    "total_amount": "278.00",
    "items_count": 2,
    "payment_options": [
      {
        "key": "full",
        "label": "Pay Full Amount",
        "payment_plan": "full",
        "pay_now_amount": "278.00",
        "pay_later_amount": "0.00",
        "payment_status_after_order": "paid"
      }
    ]
  }
}
```

Frontend should show `measurement_fee` as a separate line item in checkout.

Recommended label:

```text
Measurement fee
```

Arabic label suggestion:

```text
رسوم القياس
```

## Order Pricing Response Change

Order pricing summary now includes `measurement_fee`.

Affected order surfaces:

- Customer order detail/list
- Tailor order detail/list
- Rider order detail/list if pricing is shown
- Checkout status
- Checkout create-order response

Example:

```json
{
  "pricing_summary": {
    "subtotal": "200.00",
    "stitching_price": "0.00",
    "tax_amount": "30.00",
    "delivery_fee": "20.00",
    "system_fee": "3.00",
    "express_fee": "0.00",
    "measurement_fee": "25.00",
    "total_amount": "278.00",
    "payment_status": "pending",
    "paid_amount": "0.00",
    "remaining_amount": "278.00"
  }
}
```

## When Measurement Fee Applies

Backend applies the fee automatically when:

- order is home delivery
- selected tailor has `measurement_fee > 0`
- order needs measurement
- at least one item/person has missing measurements

Backend does not apply the fee when:

- service mode is `walk_in`
- all item/person measurements already exist
- tailor fee is `0.00`
- order does not need measurement

## Important Rule

Measurement fee is charged once per order, not per item.

Example:

- 1 item missing measurements: `measurement_fee = 25.00`
- 3 items missing measurements: `measurement_fee = 25.00`
- 5 family members missing measurements: `measurement_fee = 25.00`

Do not multiply this fee on frontend.

## What Frontend Should Not Do

Frontend should not send:

```json
{
  "measurement_fee": "25.00"
}
```

when creating checkout or order.

The backend calculates and stores the fee. Frontend only displays the returned value.

## Customer Checkout UI Tasks

Add a new row in pricing summary:

```text
Measurement fee    SAR 25.00
```

Show the row when:

- `measurement_fee` exists and is greater than `0.00`

Hide the row when:

- `measurement_fee` is missing
- `measurement_fee` is `"0.00"`
- `measurement_fee` is `null`

Use backend `total_amount` directly. Do not recalculate total manually unless only for display verification.

## Tailor UI Tasks

Add a measurement fee field in tailor settings/profile area.

Recommended input:

- numeric/decimal input
- minimum value `0`
- two decimal places
- currency label `SAR`

Save action:

```http
PATCH /api/tailors/measurement-fee/
```

Payload:

```json
{
  "measurement_fee": "25.00"
}
```

After success:

- update local displayed value from `data.measurement_fee`
- show success message

## Rider Finance Response Change

Rider transaction history now includes:

```json
{
  "earning_type": "measurement",
  "earning_type_display": "Measurement"
}
```

Delivery earning example:

```json
{
  "transaction_type": "credit",
  "source": "order",
  "earning_type": "delivery",
  "earning_type_display": "Delivery",
  "amount": "20.00"
}
```

Measurement earning example:

```json
{
  "transaction_type": "credit",
  "source": "order",
  "earning_type": "measurement",
  "earning_type_display": "Measurement",
  "amount": "25.00"
}
```

Frontend can show this in rider wallet/finance history as:

- Delivery earning
- Measurement earning

## Payment Flow Notes

Payment options now use `total_amount` including `measurement_fee`.

Frontend should continue using:

- `pricing_summary.payment_options`
- selected `payment_option`
- backend returned `total_amount`

No separate payment calculation is needed on frontend.

## Example Customer Flow

1. Customer selects tailor.
2. Customer adds items without measurements.
3. Customer calls checkout:

```http
POST /api/orders/checkout/
```

4. Backend returns pricing summary with `measurement_fee`.
5. Frontend shows measurement fee line item.
6. Customer creates order/payment using existing checkout flow.
7. Order response contains same `measurement_fee` snapshot.

## Backward Compatibility

This should not break existing frontend screens if they ignore unknown fields.

Default value is:

```json
{
  "measurement_fee": "0.00"
}
```

So existing tailors will not charge measurement fee until they set it.

## Quick Frontend Checklist

- Add tailor setting screen field for measurement fee.
- Call `GET /api/tailors/measurement-fee/` to load current value.
- Call `PATCH /api/tailors/measurement-fee/` to update value.
- Show `measurement_fee` in customer checkout pricing summary.
- Show `measurement_fee` in customer order detail pricing summary.
- Do not send measurement fee in checkout/order creation payload.
- Do not multiply measurement fee by item count.
- Use backend `total_amount` and `payment_options`.
- In rider finance, show `earning_type` as Delivery or Measurement.
