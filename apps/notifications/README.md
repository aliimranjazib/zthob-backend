# Push Notifications with Firebase Cloud Messaging

This app handles push notifications using Firebase Cloud Messaging (FCM) for Phase 1 implementation.

## Setup Instructions

### 1. Install Firebase Admin SDK

Add `firebase-admin` to your requirements:

```bash
pip install firebase-admin
```

Or add to `pyproject.toml`:
```toml
firebase-admin = "^6.0.0"
```

### 2. Firebase Project Setup

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Create a new project or select existing one
3. Go to Project Settings > Service Accounts
4. Click "Generate New Private Key"
5. Download the JSON credentials file
6. Save it securely (e.g., `firebase-credentials.json`)

### 3. Configure Django Settings

Add to your `settings.py`:

```python
# Firebase Configuration
FIREBASE_CREDENTIALS_PATH = os.path.join(BASE_DIR, 'firebase-credentials.json')

# Or use environment variable
# FIREBASE_CREDENTIALS_PATH = os.environ.get('FIREBASE_CREDENTIALS_PATH')
```

**Important:** Never commit the credentials file to version control. Add it to `.gitignore`:

```
firebase-credentials.json
*.json
```

### 4. Run Migrations

```bash
python manage.py makemigrations notifications
python manage.py migrate notifications
```

## API Endpoints

### Register FCM Token
**POST** `/api/notifications/fcm-token/register/`

Register or update FCM device token for push notifications.

**Request Body:**
```json
{
  "token": "fcm_device_token_here",
  "device_type": "android",  // "ios", "android", or "web"
  "device_id": "unique_device_id_optional"
}
```

**Response:**
```json
{
  "success": true,
  "message": "FCM token registered successfully",
  "data": {
    "id": 1,
    "token": "fcm_device_token_here",
    "device_type": "android",
    "device_id": "device_123",
    "is_active": true,
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

### Update FCM Token
**PUT** `/api/notifications/fcm-token/update/`

Update existing FCM token.

**Request Body:**
```json
{
  "token": "new_fcm_device_token",
  "device_type": "android"
}
```

### Unregister FCM Token
**POST** `/api/notifications/fcm-token/unregister/`

Deactivate FCM device token.

**Request Body:**
```json
{
  "token": "fcm_device_token_here"
}
```

Or:
```json
{
  "device_id": "device_123"
}
```

### Get Notification Logs
**GET** `/api/notifications/logs/`

Get notification history for authenticated user (last 50 notifications).

## Notification Types (Phase 1)

### 1. Order Status Notifications

Automatically sent when order status changes:

- **pending** → Customer: "Your order #ORD-12345 has been placed successfully"
- **confirmed** → Customer: "Tailor has accepted your order #ORD-12345"
- **measuring** → Customer: "Rider is on the way to take your measurements..."
- **cutting** → Customer: "Fabric cutting has started..."
- **stitching** → Customer: "Your garment is being stitched..."
- **ready_for_delivery** → Customer: "Your order is ready for delivery"
- **delivered** → Customer: "Your order has been delivered"
- **cancelled** → Customer: "Your order has been cancelled"

### 2. Payment Status Notifications

Automatically sent when payment status changes:

- **paid** → Customer: "Payment of $X.XX received for order #ORD-12345"
- **pending** → Customer: "Payment pending for order #ORD-12345"
- **refunded** → Customer: "Refund of $X.XX has been processed..."

### 3. Rider Assignment Notifications

Automatically sent when rider accepts an order:

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

## Integration Points

Notifications are automatically sent from:

1. **Order Status Updates** (`apps/orders/serializers.py`)
   - When order status changes via `OrderUpdateSerializer.update()`
   - When rider updates order status via `RiderUpdateOrderStatusView`

2. **Payment Status Updates** (`apps/orders/views.py`)
   - When payment status changes via `OrderPaymentStatusUpdateView`

3. **Rider Assignment** (`apps/riders/views.py`)
   - When rider accepts order via `RiderAcceptOrderView`

## Testing

### Test Notification Sending

You can test notifications using Django shell:

```python
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

## Troubleshooting

### Firebase Not Initialized Error

Make sure:
1. Firebase credentials file exists at the configured path
2. Credentials file is valid JSON
3. File permissions are correct

### Notifications Not Received

1. Check if FCM token is registered: `GET /api/notifications/logs/`
2. Check notification logs in admin panel
3. Verify Firebase project configuration
4. Check device FCM token is valid

### Invalid Token Errors

FCM tokens can become invalid. The system automatically:
- Marks invalid tokens as inactive
- Logs errors in NotificationLog
- Continues sending to other valid tokens

## Security Notes

- FCM tokens are user-specific and require authentication
- Tokens are automatically deactivated if invalid
- Notification logs are stored for audit purposes
- Never expose Firebase credentials in client-side code

## Next Steps (Future Phases)

- Phase 2: Profile approval/rejection notifications
- Phase 3: Appointment reminders
- Phase 4: Marketing notifications
- User notification preferences
- Quiet hours
- Notification categories enable/disable

