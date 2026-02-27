# Phone-Based Authentication Implementation

## Overview
This document describes the phone-based authentication system that allows users to login/register using only their phone number and OTP verification, without requiring passwords.

## Implementation Summary

### 1. Model Changes (`apps/accounts/models.py`)
- **Email**: Made optional (nullable) - users can register without email
- **Phone**: Made unique with database index - ensures one account per phone number
- **REQUIRED_FIELDS**: Removed email requirement

### 2. New Serializers (`apps/accounts/serializers.py`)
- **PhoneLoginSerializer**: Validates phone number format (Saudi format: 05xxxxxxxx)
- **PhoneVerifySerializer**: Validates OTP code and optional user info (name, role)

### 3. New Service Methods (`apps/core/services.py`)
- **normalize_phone_to_local()**: Converts various phone formats to local format (05xxxxxxxx)
- **create_verification_for_phone()**: Creates OTP verification for phone-based auth (finds or creates user)
- **verify_otp_for_phone()**: Verifies OTP and returns authenticated user

### 4. New API Endpoints (`apps/accounts/views.py`)

#### POST `/api/accounts/phone-login/`
Sends OTP to phone number for login/registration.

**Request:**
```json
{
  "phone": "0501234567"
}
```

**Response:**
```json
{
  "success": true,
  "message": "OTP sent to 0501234567",
  "data": {
    "phone": "0501234567",
    "sms_sent": true,
    "expires_in": 300
  }
}
```

#### POST `/api/accounts/phone-verify/`
Verifies OTP and completes login/registration. Auto-creates user if doesn't exist.

**Request:**
```json
{
  "phone": "0501234567",
  "otp_code": "123456",
  "name": "Ahmed Ali",  // Optional - only for new users
  "role": "USER"        // Optional - defaults to "USER"
}
```

**Response (New User - 201 Created):**
```json
{
  "success": true,
  "message": "Registration and login successful",
  "data": {
    "tokens": {
      "access_token": "...",
      "refresh_token": "..."
    },
    "user": {
      "id": 123,
      "phone": "0501234567",
      "first_name": "Ahmed",
      "last_name": "Ali",
      "email": null,
      "role": "USER",
      "phone_verified": true
    },
    "is_new_user": true
  }
}
```

**Response (Existing User - 200 OK):**
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

#### POST `/api/accounts/phone-resend-otp/`
Resends OTP if user didn't receive it or it expired.

**Request:**
```json
{
  "phone": "0501234567"
}
```

**Response:** Same as phone-login endpoint

### 5. Database Migration
- **File**: `apps/accounts/migrations/0002_phone_unique_email_optional.py`
- Handles existing data by setting duplicate phones to null
- Makes phone unique and email optional

### 6. Test Cases (`apps/accounts/tests_phone_auth.py`)
Comprehensive test suite covering:
- OTP sending and validation
- New user registration
- Existing user login
- Invalid/expired OTP handling
- Phone format validation
- JWT token generation and usage
- User data updates

## Authentication Flow

### For New Users:
1. User enters phone number → `POST /api/accounts/phone-login/`
2. System sends OTP via SMS
3. User enters OTP + optional name/role → `POST /api/accounts/phone-verify/`
4. System creates user account and returns JWT tokens
5. User is logged in and can use access_token for API calls

### For Existing Users:
1. User enters phone number → `POST /api/accounts/phone-login/`
2. System sends OTP via SMS
3. User enters OTP → `POST /api/accounts/phone-verify/`
4. System verifies OTP and returns JWT tokens
5. User is logged in

## Key Features

1. **Passwordless Authentication**: No passwords required
2. **Auto-Registration**: New users are automatically created on first OTP verification
3. **Flexible Phone Formats**: Accepts multiple formats (05xxxxxxxx, +9665xxxxxxxx, etc.)
4. **JWT Token Compatible**: Uses same JWT tokens as existing auth system
5. **Backward Compatible**: Existing email/password endpoints still work
6. **OTP Expiration**: OTPs expire after 5 minutes
7. **SMS Integration**: Uses existing Twilio service for OTP delivery

## Phone Number Formats Supported

- `0501234567` (Standard Saudi format)
- `501234567` (Without leading 0)
- `+966501234567` (E.164 format)
- `966501234567` (With country code)

All formats are normalized to `05xxxxxxxx` for storage.

## Security Considerations

1. **OTP Expiration**: 5 minutes
2. **Unique Phone Constraint**: One account per phone number
3. **Phone Verification**: Users must verify phone before account is fully activated
4. **JWT Token Security**: Same security as existing authentication

## Testing

Run tests with:
```bash
python manage.py test apps.accounts.tests_phone_auth
```

## Migration Instructions

1. Run migration:
   ```bash
   python manage.py migrate accounts
   ```

2. Test endpoints using Postman or similar tool

3. Update mobile app to use new endpoints:
   - Replace login flow with phone-login → phone-verify
   - Remove password fields from UI
   - Handle `is_new_user` flag to show onboarding if needed

## Backward Compatibility

- Existing `/api/accounts/login/` endpoint still works (email/password)
- Existing `/api/accounts/register/` endpoint still works
- All existing JWT-protected endpoints work with tokens from phone auth
- Existing users can continue using email/password login

## Notes

- Email is now optional but can still be added later via profile update
- Phone number is required and unique for phone-based auth
- Users created via phone auth get auto-generated usernames (user_05xxxxxxxx)
- OTP is stored in PhoneVerification model with 5-minute expiration

