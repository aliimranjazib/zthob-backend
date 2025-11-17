# Push Notifications Implementation - Phase 1 ✅

## Overview

Phase 1 of push notifications using Firebase Cloud Messaging (FCM) has been successfully implemented. This includes:

1. ✅ Order status change notifications
2. ✅ Payment status notifications  
3. ✅ Rider assignment notifications

## What Was Implemented

### 1. New Notifications App (`apps/notifications/`)

- **Models:**
  - `FCMDeviceToken` - Stores user device tokens for push notifications
  - `NotificationLog` - Logs all sent notifications for tracking and debugging

- **Services:**
  - `NotificationService` - Handles sending push notifications via FCM
    - `send_notification()` - Send notification to a user
    - `send_order_status_notification()` - Order status change notifications
    - `send_payment_status_notification()` - Payment status notifications
    - `send_rider_assignment_notification()` - Rider assignment notifications

- **API Endpoints:**
  - `POST /api/notifications/fcm-token/register/` - Register FCM token
  - `PUT /api/notifications/fcm-token/update/` - Update FCM token
  - `POST /api/notifications/fcm-token/unregister/` - Unregister FCM token
  - `GET /api/notifications/logs/` - Get notification history

### 2. Integration Points

Notifications are automatically sent from:

- **Order Status Updates:**
  - `apps/orders/serializers.py` - `OrderUpdateSerializer.update()`
  - `apps/riders/views.py` - `RiderUpdateOrderStatusView`

- **Payment Status Updates:**
  - `apps/orders/views.py` - `OrderPaymentStatusUpdateView`

- **Rider Assignment:**
  - `apps/riders/views.py` - `RiderAcceptOrderView`

## Setup Instructions

### Step 1: Install Dependencies

```bash
pip install firebase-admin
# Or update requirements.txt
pip install -r requirements.txt
```

### Step 2: Firebase Project Setup

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Create a new project or select existing one
3. Go to **Project Settings** > **Service Accounts**
4. Click **"Generate New Private Key"**
5. Download the JSON credentials file
6. Save it as `firebase-credentials.json` in your project root

### Step 3: Configure Django Settings

Add to `zthob/settings.py`:

```python
# Firebase Configuration
FIREBASE_CREDENTIALS_PATH = os.path.join(BASE_DIR, 'firebase-credentials.json')

# Or use environment variable (recommended for production)
# FIREBASE_CREDENTIALS_PATH = os.environ.get('FIREBASE_CREDENTIALS_PATH')
```

**Important:** Add to `.gitignore`:
```
firebase-credentials.json
```

### Step 4: Run Migrations

```bash
python manage.py migrate notifications
```

## API Usage

### Register FCM Token (Mobile App)

When user logs in or app starts, register their FCM token:

```bash
POST /api/notifications/fcm-token/register/
Authorization: Bearer <access_token>

{
  "token": "fcm_device_token_from_firebase",
  "device_type": "android",  // or "ios", "web"
  "device_id": "unique_device_id"  // optional
}
```

### Unregister FCM Token (On Logout)

```bash
POST /api/notifications/fcm-token/unregister/
Authorization: Bearer <access_token>

{
  "token": "fcm_device_token"
}
```

## Notification Types

### Order Status Notifications

Automatically sent to relevant users when order status changes:

| Status | Customer Notification | Tailor Notification | Rider Notification |
|--------|----------------------|---------------------|-------------------|
| `pending` | "Your order #ORD-12345 has been placed successfully" | "New order #ORD-12345 received" | - |
| `confirmed` | "Tailor has accepted your order #ORD-12345" | "You have confirmed order #ORD-12345" | - |
| `measuring` | "Rider is on the way to take your measurements..." | - | "Please take measurements for order #ORD-12345" |
| `cutting` | "Fabric cutting has started..." | "Order #ORD-12345 is ready for cutting" | - |
| `stitching` | "Your garment is being stitched..." | "Order #ORD-12345 is ready for stitching" | - |
| `ready_for_delivery` | "Your order is ready for delivery" | "Order #ORD-12345 is ready for pickup" | "Order #ORD-12345 is ready for pickup" |
| `delivered` | "Your order has been delivered" | "Order #ORD-12345 has been delivered" | "Order #ORD-12345 delivery completed" |
| `cancelled` | "Your order has been cancelled" | "Order #ORD-12345 has been cancelled" | "Order #ORD-12345 has been cancelled" |

### Payment Status Notifications

| Status | Customer Notification | Tailor Notification |
|--------|----------------------|---------------------|
| `paid` | "Payment of $X.XX received for order #ORD-12345" | "Payment received for order #ORD-12345 - $X.XX" |
| `pending` | "Payment pending for order #ORD-12345" | - |
| `refunded` | "Refund of $X.XX has been processed..." | "Refund issued for order #ORD-12345" |

### Rider Assignment Notifications

When rider accepts an order:

- **Customer**: "Rider [Name] has been assigned to deliver your order #ORD-12345"
- **Tailor**: "Rider [Name] will pick up order #ORD-12345"
- **Rider**: "You have been assigned to order #ORD-12345"

## Notification Payload Structure

```json
{
  "notification": {
    "title": "Order #ORD-12345 Update",
    "body": "Tailor has accepted your order"
  },
  "data": {
    "type": "ORDER_STATUS",
    "category": "order_confirmed",
    "order_id": "123",
    "order_number": "ORD-12345",
    "status": "confirmed",
    "old_status": "pending"
  }
}
```

## Testing

### Test Notification Sending

```python
# Django shell
python manage.py shell

from apps.notifications.services import NotificationService
from apps.accounts.models import CustomUser

user = CustomUser.objects.get(id=1)
NotificationService.send_notification(
    user=user,
    title="Test Notification",
    body="This is a test notification",
    notification_type="SYSTEM",
    category="test",
    data={"test": "true"}
)
```

### Check Notification Logs

```bash
GET /api/notifications/logs/
Authorization: Bearer <access_token>
```

Or check in Django Admin: `/admin/notifications/notificationlog/`

## Error Handling

- Notifications are sent asynchronously and don't block the main request
- If Firebase is not configured, errors are logged but don't fail the operation
- Invalid FCM tokens are automatically deactivated
- All notification attempts are logged in `NotificationLog` model

## Files Created/Modified

### New Files:
- `apps/notifications/__init__.py`
- `apps/notifications/apps.py`
- `apps/notifications/models.py`
- `apps/notifications/services.py`
- `apps/notifications/serializers.py`
- `apps/notifications/views.py`
- `apps/notifications/urls.py`
- `apps/notifications/admin.py`
- `apps/notifications/migrations/0001_initial.py`
- `apps/notifications/README.md`

### Modified Files:
- `zthob/settings.py` - Added notifications app to INSTALLED_APPS
- `zthob/urls.py` - Added notifications URLs
- `apps/orders/serializers.py` - Added notification on order status update
- `apps/orders/views.py` - Added notification on payment status update
- `apps/riders/views.py` - Added notifications on rider assignment and status update
- `pyproject.toml` - Added firebase-admin dependency

## Next Steps

1. **Configure Firebase:**
   - Download Firebase credentials JSON file
   - Add `FIREBASE_CREDENTIALS_PATH` to settings.py
   - Run migrations: `python manage.py migrate`

2. **Mobile App Integration:**
   - Implement FCM token registration in mobile app
   - Register token on login/app start
   - Handle notification payloads in app

3. **Testing:**
   - Test order status change notifications
   - Test payment status notifications
   - Test rider assignment notifications

4. **Future Phases:**
   - Phase 2: Profile approval/rejection notifications
   - Phase 3: Appointment reminders
   - Phase 4: Marketing notifications
   - User notification preferences
   - Quiet hours settings

## Troubleshooting

### Firebase Not Initialized
- Check if `FIREBASE_CREDENTIALS_PATH` is set in settings
- Verify credentials file exists and is valid JSON
- Check file permissions

### Notifications Not Received
- Verify FCM token is registered: Check `/api/notifications/logs/`
- Check notification logs in admin panel for errors
- Verify Firebase project configuration
- Ensure device FCM token is valid

### Invalid Token Errors
- Tokens are automatically deactivated if invalid
- Check `NotificationLog` for error messages
- Re-register token from mobile app

## Support

For issues or questions:
1. Check notification logs in Django Admin
2. Review `apps/notifications/README.md` for detailed documentation
3. Check Django logs for Firebase initialization errors

