# MyFatoorah Flutter SDK Integration

This document is for the Flutter application developer.

The application operates only in Saudi Arabia:

- MyFatoorah country: Saudi Arabia
- Currency: `SAR`
- Flutter handles the MyFatoorah payment UI and 3DS flow.
- The backend calculates the amount and verifies the payment.
- Flutter must never mark an order as paid from the SDK result alone.
- Flutter must not call `checkout/create-order` for online payments.

## 1. Flutter Package

Add the current approved MyFatoorah Flutter package version to `pubspec.yaml`:

```yaml
dependencies:
  myfatoorah_flutter: ^3.2.1
```

Install it:

```bash
flutter pub get
```

Import it:

```dart
import 'package:myfatoorah_flutter/myfatoorah_flutter.dart';
```

## 2. Initialize MyFatoorah for Saudi Arabia

Initialize the SDK once when the application starts:

```dart
void initializeMyFatoorah() {
  MFSDK.init(
    const String.fromEnvironment('MYFATOORAH_API_KEY'),
    MFCountry.SAUDIARABIA,
    MFEnvironment.LIVE,
  );
}
```

Use `MFEnvironment.TEST` during testing and `MFEnvironment.LIVE` only for the
production build.

Do not print the API key, card information, SDK request, or complete SDK response
to the application logs.

## 3. Overall Online Payment Flow

```text
Create checkout
    -> Prepare backend payment attempt
    -> Execute payment with MyFatoorah Flutter SDK
    -> Receive invoiceId
    -> Confirm invoice with backend
    -> Poll checkout status when necessary
    -> Open order when status becomes order_created
```

## 4. Create Checkout

Use the existing checkout endpoint:

```http
POST /api/orders/checkout/
Authorization: Bearer <customer-access-token>
Content-Type: application/json
```

Example request:

```json
{
  "tailor": 12,
  "order_type": "fabric_only",
  "service_mode": "home_delivery",
  "payment_method": "credit_card",
  "delivery_address": 25,
  "items": [
    {
      "fabric": 41,
      "quantity": 1,
      "measurements": {}
    }
  ]
}
```

Example response:

```json
{
  "success": true,
  "message": "Checkout created successfully",
  "data": {
    "bookingUniqueKey": "chk_abc123",
    "status": "active",
    "pricing_summary": {
      "total_amount": "135.00"
    },
    "expires_at": "2026-07-16T12:00:00Z",
    "order_id": null
  },
  "errors": null
}
```

Store `bookingUniqueKey`. Do not use the checkout amount directly for the SDK;
the payment amount must come from the prepare endpoint below.

## 5. Prepare Online Payment

```http
POST /api/orders/checkout/myfatoorah/prepare/
Authorization: Bearer <customer-access-token>
Content-Type: application/json
```

Request:

```json
{
  "bookingUniqueKey": "chk_abc123",
  "payment_option": "full",
  "idempotency_key": "4be96e6e-eec5-44cc-8c98-d66caae17831"
}
```

Valid `payment_option` values:

```text
full
advance_50
advance_30
```

Generate one UUID when the user starts a payment attempt. Reuse the same UUID
when retrying the same prepare request. Generate a new UUID only for a genuinely
new payment attempt.

Successful response (`201`, or `200` when the same idempotency key is retried):

```json
{
  "success": true,
  "message": "MyFatoorah payment attempt prepared.",
  "data": {
    "attempt_reference": "mfp_36e69ec9fb3642cd87e658807b80f497",
    "customer_reference": "mfp_36e69ec9fb3642cd87e658807b80f497",
    "user_defined_field": "mfp_36e69ec9fb3642cd87e658807b80f497",
    "invoice_id": null,
    "amount": "135.00",
    "currency": "SAR",
    "payment_option": "full",
    "status": "prepared",
    "expires_at": "2026-07-16T12:00:00Z",
    "order_id": null
  },
  "errors": null
}
```

Store all of these values until payment finishes:

```text
bookingUniqueKey
attempt_reference
amount
currency
payment_option
idempotency_key
```

## 6. Get MyFatoorah Payment Methods

Use the exact amount returned by the backend:

```dart
Future<MFInitiatePaymentResponse> loadPaymentMethods({
  required String amount,
}) async {
  final request = MFInitiatePaymentRequest(
    invoiceAmount: double.parse(amount),
    currencyIso: MFCurrencyISO.SAUDIARABIA_SAR,
  );

  return MFSDK.initiatePayment(request, MFLanguage.ENGLISH);
}
```

Display only payment methods returned and enabled by MyFatoorah. Do not hardcode
a payment method ID because IDs can differ by account and environment.

## 7. Execute Payment with the SDK

After the customer selects a MyFatoorah payment method:

```dart
Future<void> executePayment({
  required int paymentMethodId,
  required String amount,
  required String attemptReference,
  required Future<void> Function(String invoiceId) confirmInvoice,
}) async {
  final request = MFExecutePaymentRequest(
    invoiceValue: double.parse(amount),
  );

  request.paymentMethodId = paymentMethodId;
  request.displayCurrencyIso = MFCurrencyISO.SAUDIARABIA_SAR;
  request.customerReference = attemptReference;
  request.userDefinedField = attemptReference;

  try {
    await MFSDK.executePayment(
      request,
      MFLanguage.ENGLISH,
      (invoiceId) async {
        // This callback can happen before the payment reaches its final status.
        // Attach and verify the invoice immediately.
        await confirmInvoice(invoiceId);
      },
    );
  } catch (error) {
    // Show a generic payment failure/cancellation message.
    // Do not create an order and do not mark payment as successful here.
  }
}
```

For Arabic MyFatoorah UI, use `MFLanguage.ARABIC`.

The two critical reference fields must contain the backend attempt reference:

```dart
request.customerReference = attemptReference;
request.userDefinedField = attemptReference;
```

The backend rejects an otherwise successful invoice if neither field matches the
prepared attempt.

## 8. Confirm the MyFatoorah Invoice

Call confirmation as soon as `onInvoiceCreated` returns an invoice ID. It is safe
to call the endpoint again after the SDK completes or when the application resumes.

```http
POST /api/orders/checkout/myfatoorah/confirm/
Authorization: Bearer <customer-access-token>
Content-Type: application/json
```

Request:

```json
{
  "attempt_reference": "mfp_36e69ec9fb3642cd87e658807b80f497",
  "invoice_id": "12345678"
}
```

### Verified Success: HTTP 200

```json
{
  "success": true,
  "message": "MyFatoorah payment confirmed successfully.",
  "data": {
    "attempt_reference": "mfp_36e69ec9fb3642cd87e658807b80f497",
    "invoice_id": "12345678",
    "amount": "135.00",
    "currency": "SAR",
    "payment_option": "full",
    "status": "succeeded",
    "order_id": 482,
    "order": {
      "id": 482,
      "payment_status": "paid",
      "payment_method": "credit_card"
    }
  },
  "errors": null
}
```

Navigate to the order-success screen only after this response or after checkout
polling reports `order_created`.

### Still Processing: HTTP 202

```json
{
  "success": true,
  "message": "Payment is not completed yet.",
  "data": {
    "attempt_reference": "mfp_36e69ec9fb3642cd87e658807b80f497",
    "invoice_id": "12345678",
    "amount": "135.00",
    "currency": "SAR",
    "status": "pending",
    "order_id": null
  },
  "errors": null
}
```

Start polling the checkout-status endpoint. Do not show payment failure for `202`.

### Rejected Payment: HTTP 400

This can mean the invoice, amount, currency, or payment reference does not match.
Do not create an order. Show the backend message and send the user to support when
the SDK indicates money was charged.

### Manual Review: HTTP 409

```json
{
  "success": false,
  "message": "Payment was received but requires manual review. Please contact support.",
  "data": {
    "status": "requires_review",
    "order_id": 482
  },
  "errors": null
}
```

Do not retry payment when status is `requires_review`.

### Temporary Verification Failure: HTTP 502 or 503

The payment result is unknown. Keep the attempt reference and invoice ID, show a
processing message, and retry confirmation with backoff. Do not start another
payment immediately.

## 9. Poll Checkout Status

Poll every 2 to 3 seconds after confirmation returns `202`, when the app resumes,
or when the SDK closes without a clear final result:

```http
GET /api/orders/checkout/{bookingUniqueKey}/
Authorization: Bearer <customer-access-token>
```

Example:

```http
GET /api/orders/checkout/chk_abc123/
```

Example completed response:

```json
{
  "success": true,
  "message": "Checkout status retrieved successfully",
  "data": {
    "bookingUniqueKey": "chk_abc123",
    "status": "order_created",
    "payment_method": "credit_card",
    "payment_option": "full",
    "payment_reference": "07070000000000000001",
    "order_id": 482
  },
  "errors": null
}
```

Handle statuses as follows:

| Status | Flutter behavior |
|---|---|
| `active` | Checkout exists; payment has not started |
| `payment_initiated` | Continue waiting or confirming the invoice |
| `order_created` | Open success/order screen |
| `payment_failed` | Show payment failure and allow a new attempt |
| `expired` | Create a new checkout |
| `cancelled` | Stop payment flow |

Stop polling after a terminal status or after a reasonable UI timeout. If the UI
times out, keep the references and let the user refresh payment status later.

## 10. COD Flow

COD does not use the MyFatoorah SDK.

```http
POST /api/orders/checkout/create-order/
Authorization: Bearer <customer-access-token>
Content-Type: application/json
```

```json
{
  "bookingUniqueKey": "chk_abc123",
  "payment_method": "cod"
}
```

Never send `credit_card` to `checkout/create-order`.

## 11. Remaining-Balance Payment

### Prepare

```http
POST /api/orders/{orderId}/pay-remaining/myfatoorah/prepare/
Authorization: Bearer <customer-access-token>
Content-Type: application/json
```

```json
{
  "idempotency_key": "78f4806a-ab22-4d55-92a9-fe256e778a25"
}
```

Example response:

```json
{
  "success": true,
  "message": "MyFatoorah remaining payment attempt prepared.",
  "data": {
    "attempt_reference": "mfp_remaining123",
    "customer_reference": "mfp_remaining123",
    "user_defined_field": "mfp_remaining123",
    "amount": "67.50",
    "currency": "SAR",
    "payment_option": "remaining_balance",
    "status": "prepared",
    "order_id": 482,
    "bookingUniqueKey": "rem_abc123"
  },
  "errors": null
}
```

Run the SDK using the returned amount and attempt reference exactly as described
for checkout payment.

### Confirm

```http
POST /api/orders/{orderId}/pay-remaining/myfatoorah/confirm/
Authorization: Bearer <customer-access-token>
Content-Type: application/json
```

```json
{
  "attempt_reference": "mfp_remaining123",
  "invoice_id": "87654321"
}
```

On HTTP `200`, refresh the order. The backend updates `paid_amount`,
`remaining_amount`, and `payment_status`.

## 12. Required Flutter State

Persist this non-sensitive payment state until the flow reaches a terminal status:

```dart
class PendingMyFatoorahPayment {
  final String bookingUniqueKey;
  final String attemptReference;
  final String amount;
  final String currency;
  final String paymentOption;
  final String idempotencyKey;
  final String? invoiceId;
}
```

When the app launches or resumes and an unfinished payment exists:

1. If `invoiceId` exists, call the confirm endpoint again.
2. Poll checkout status.
3. Clear local pending state only after `order_created`, confirmed failure, expiry,
   or manual-review handling.

## 13. Rules the Frontend Must Follow

1. Use only the amount returned by the prepare endpoint.
2. Currency must always be `SAR`.
3. Set both MyFatoorah reference fields to `attempt_reference`.
4. Send `invoiceId` to the backend immediately.
5. Treat backend confirmation or backend checkout status as authoritative.
6. Never create an online-paid order from Flutter.
7. Never reuse an attempt reference with a different invoice.
8. Never start another payment after HTTP `202`, `502`, or `503` without checking
   the existing attempt first.
9. Never retry a `requires_review` payment.
10. Never log card data, API keys, invoice responses, customer details, or tokens.

## 14. Flutter QA Checklist

- Test full payment.
- Test 50% advance payment.
- Test 30% advance payment.
- Test remaining-balance payment.
- Test SDK cancellation.
- Test 3DS success and failure.
- Test app termination during 3DS.
- Test app resume with a stored invoice ID.
- Test confirmation returning `202`.
- Test backend temporarily returning `502` or `503`.
- Test duplicate tapping on the Pay button.
- Test Arabic and English MyFatoorah UI.
- Confirm COD never opens MyFatoorah.
- Confirm only one order is shown after repeated confirmation calls.
