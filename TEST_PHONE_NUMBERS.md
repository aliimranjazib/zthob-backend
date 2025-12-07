# Test Phone Numbers for OTP Testing

## 🧪 Test Mode Implementation

For development and testing purposes, we've added test phone numbers that bypass SMS and always return a fixed OTP.

## Test Phone Numbers

You can use any of these phone numbers for testing:

- `0500000000`
- `0511111111`
- `0599999999`

## Fixed Test OTP

**All test phone numbers use OTP: `123456`**

## How to Use

### Step 1: Request OTP
```bash
POST /api/accounts/phone-login/
Content-Type: application/json

{
  "phone": "0500000000"
}
```

**Response:**
```json
{
  "success": true,
  "message": "OTP sent to 0500000000",
  "data": {
    "phone": "0500000000",
    "sms_sent": true,
    "expires_in": 300
  }
}
```

**Note:** You'll also see in your server console:
```
🧪 TEST MODE: OTP for 0500000000 is 123456
```

### Step 2: Verify OTP
```bash
POST /api/accounts/phone-verify/
Content-Type: application/json

{
  "phone": "0500000000",
  "otp_code": "123456"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Login successful",
  "data": {
    "tokens": {
      "access_token": "...",
      "refresh_token": "..."
    },
    "user": { ... },
    "is_new_user": false
  }
}
```

## Benefits

✅ **No SMS sent** - Saves SMS costs during development  
✅ **Instant testing** - No need to wait for SMS  
✅ **Fixed OTP** - Always use `123456`  
✅ **Console output** - OTP printed in server logs  
✅ **Works like production** - Same flow, just bypasses SMS  

## Customization

To change test phone numbers or OTP, edit `apps/core/services.py`:

```python
# Test phone numbers for development/testing
TEST_PHONES = ['0500000000', '0511111111', '0599999999']  # Add your numbers
TEST_OTP = '123456'  # Change to your preferred test OTP
```

## Important Notes

⚠️ **Production Safety:** Test phone numbers only work in development. Real phone numbers will still send SMS.

⚠️ **Security:** Never use test phone numbers in production. They're only for local development.

⚠️ **OTP Expiration:** Test OTPs still expire after 5 minutes (same as real OTPs).

## Testing Workflow

1. Use test phone: `0500000000`
2. Request OTP → Get success response
3. Check console for OTP: `123456`
4. Verify with OTP: `123456`
5. Get JWT tokens → Use for API calls

## Example Postman Collection

```json
{
  "name": "Phone Auth Test",
  "requests": [
    {
      "name": "Send OTP (Test)",
      "method": "POST",
      "url": "{{base_url}}/api/accounts/phone-login/",
      "body": {
        "phone": "0500000000"
      }
    },
    {
      "name": "Verify OTP (Test)",
      "method": "POST",
      "url": "{{base_url}}/api/accounts/phone-verify/",
      "body": {
        "phone": "0500000000",
        "otp_code": "123456"
      }
    }
  ]
}
```

