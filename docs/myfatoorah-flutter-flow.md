# MyFatoorah Flutter Checkout Flow (Saudi Arabia)

This integration uses the MyFatoorah Flutter SDK for payment UI and Django as the
only authority that can mark a payment successful or create a paid order.

## Fixed KSA Configuration

- Flutter country: `MFCountry.SAUDIARABIA`
- Flutter currency: `MFCurrencyISO.SAUDIARABIA_SAR`
- Backend live API: `https://api-sa.myfatoorah.com`
- Currency: `SAR`

Do not calculate or modify the payment amount in Flutter. Always use the amount
returned by the prepare endpoint.

## Checkout Payment

### 1. Create the checkout

Use the existing checkout endpoint and retain its `bookingUniqueKey`.

### 2. Prepare a payment attempt

```http
POST /api/orders/checkout/myfatoorah/prepare/
Authorization: Bearer <access-token>
Content-Type: application/json
```

```json
{
  "bookingUniqueKey": "chk_...",
  "payment_option": "full",
  "idempotency_key": "one-uuid-per-pay-button-attempt"
}
```

The response contains:

```json
{
  "attempt_reference": "mfp_...",
  "customer_reference": "mfp_...",
  "user_defined_field": "mfp_...",
  "amount": "135.00",
  "currency": "SAR",
  "status": "prepared"
}
```

Valid checkout payment options are `full`, `advance_50`, and `advance_30`.

### 3. Execute with the Flutter SDK

Build `MFExecutePaymentRequest` with the exact backend amount. Set both
`customerReference` and `userDefinedField` to the returned attempt reference.
Set the display currency to Saudi riyals.

Never log the MyFatoorah API key, card information, SDK result payload, or customer
payment data.

### 4. Confirm the invoice

Call this endpoint as soon as the SDK's `onInvoiceCreated` callback provides the
invoice ID. It is safe to call it again after the SDK finishes.

```http
POST /api/orders/checkout/myfatoorah/confirm/
Authorization: Bearer <access-token>
Content-Type: application/json
```

```json
{
  "attempt_reference": "mfp_...",
  "invoice_id": "12345678"
}
```

Responses:

- `200`: payment verified and order created, or already processed
- `202`: invoice exists but payment is still pending
- `400`: expired, mismatched, reused, or invalid payment
- `502`/`503`: temporary gateway/configuration failure; retry confirmation safely

The backend verifies invoice status, successful transaction status, exact amount,
`SAR` currency, attempt reference, invoice uniqueness, and checkout ownership.

### 5. Read final status

Continue polling the existing endpoint when confirmation returns `202` or the app
resumes after interruption:

```http
GET /api/orders/checkout/{bookingUniqueKey}/
```

The signed webhook can create the order even when Flutter never receives its final
SDK callback.

## Remaining Balance

Prepare:

```http
POST /api/orders/{order_id}/pay-remaining/myfatoorah/prepare/
```

```json
{
  "idempotency_key": "one-uuid-per-pay-button-attempt"
}
```

Confirm using the returned attempt reference:

```http
POST /api/orders/{order_id}/pay-remaining/myfatoorah/confirm/
```

```json
{
  "attempt_reference": "mfp_...",
  "invoice_id": "12345678"
}
```

## MyFatoorah Portal Webhook

Configure Webhook V2 for `PAYMENT_STATUS_CHANGED`:

```text
https://app.mgask.net/api/orders/checkout/myfatoorah/webhook/
```

Set the same generated webhook secret in the portal and the backend environment.
The endpoint verifies `myfatoorah-signature`, deduplicates event references, and
performs a server-to-server payment inquiry before changing order state.

## Backend Environment

```text
MYFATOORAH_API_KEY=<server-api-key>
MYFATOORAH_WEBHOOK_SECRET=<portal-webhook-secret>
MYFATOORAH_API_BASE_URL=https://api-sa.myfatoorah.com
MYFATOORAH_TIMEOUT_SECONDS=30
```

Apply database migrations before enabling the Flutter flow:

```bash
uv run python manage.py migrate
```
