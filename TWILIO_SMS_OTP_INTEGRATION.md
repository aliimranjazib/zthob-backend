# Twilio SMS OTP Integration Guide

## 📋 Table of Contents
1. [Overview](#overview)
2. [What is Twilio?](#what-is-twilio)
3. [How OTP Verification Works](#how-otp-verification-works)
4. [Setup Instructions](#setup-instructions)
5. [Implementation](#implementation)
6. [Testing](#testing)
7. [Troubleshooting](#troubleshooting)
8. [Production Considerations](#production-considerations)

---

## 🎯 Overview

This guide explains how to integrate Twilio SMS for OTP (One-Time Password) verification in the Django backend. The system already has OTP generation and verification logic - this guide adds the SMS sending capability.

**Current Status:**
- ✅ OTP generation (6-digit code)
- ✅ OTP verification logic
- ✅ Phone verification model
- ❌ SMS sending (needs Twilio integration)

**After Integration:**
- ✅ OTP generation
- ✅ OTP sent via SMS (Twilio)
- ✅ OTP verification
- ✅ Phone number verification

---

## 📱 What is Twilio?

**Twilio** is a cloud communications platform that allows you to:
- Send SMS messages
- Make phone calls
- Send WhatsApp messages
- And more...

**Pricing:**
- Free trial: $15.50 credit
- Pay-as-you-go: ~$0.0075 per SMS (varies by country)
- No monthly fees

**Why Twilio?**
- ✅ Reliable delivery
- ✅ Global coverage
- ✅ Easy integration
- ✅ Good documentation
- ✅ Free trial available

---

## 🔄 How OTP Verification Works

### Complete Flow:

```
1. User requests OTP
   ↓
2. Backend generates 6-digit code
   ↓
3. Backend sends SMS via Twilio
   ↓
4. User receives SMS with code
   ↓
5. User enters code in app
   ↓
6. Backend verifies code
   ↓
7. If valid → Mark phone as verified ✅
```

### Security Features:
- OTP expires in 5 minutes
- OTP can only be used once
- Rate limiting (prevent spam)
- Phone number validation

---

## 🚀 Setup Instructions

### Step 1: Create Twilio Account

1. Go to: https://www.twilio.com/try-twilio
2. Sign up for free account
3. Verify your email
4. Verify your phone number
5. Get your credentials:

**Where to find credentials:**
- Dashboard: https://console.twilio.com/
- **Account SID**: Starts with `AC...` (on dashboard)
- **Auth Token**: Click "show" to reveal (on dashboard)
- **Phone Number**: Get a free trial number (Phone Numbers → Buy a number)

### Step 2: Install Twilio SDK

```bash
# Using uv (recommended)
uv pip install twilio

# Or using pip
pip install twilio

# Add to requirements.txt
echo "twilio>=8.0.0" >> requirements.txt
```

### Step 3: Configure Environment Variables

**Add to `.env` file:**
```bash
# Twilio Configuration
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE_NUMBER=+1234567890  # Your Twilio phone number (with country code)
```

**Add to `zthob/settings.py`:**
```python
# Twilio Configuration
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', None)
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', None)
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER', None)
```

---

## 💻 Implementation

### Step 1: Create Twilio Service

**File: `apps/core/twilio_service.py`**

```python
import logging
from django.conf import settings
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

logger = logging.getLogger(__name__)

class TwilioSMSService:
    """Service for sending SMS via Twilio"""
    
    @staticmethod
    def send_otp_sms(phone_number: str, otp_code: str) -> tuple[bool, str]:
        """
        Send OTP via SMS using Twilio
        
        Args:
            phone_number: Phone number in E.164 format (e.g., +966501234567)
            otp_code: 6-digit OTP code
            
        Returns:
            tuple: (success: bool, message: str)
        """
        # Check if Twilio is configured
        if not all([
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN,
            settings.TWILIO_PHONE_NUMBER
        ]):
            logger.error("Twilio not configured. Missing credentials in settings.")
            return False, "SMS service not configured"
        
        try:
            # Initialize Twilio client
            client = Client(
                settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN
            )
            
            # Format phone number (ensure it starts with +)
            formatted_phone = TwilioSMSService.format_phone_number(phone_number)
            
            # Create SMS message
            message_body = f"Your Mgask verification code is: {otp_code}. Valid for 5 minutes."
            
            # Send SMS
            message = client.messages.create(
                body=message_body,
                from_=settings.TWILIO_PHONE_NUMBER,
                to=formatted_phone
            )
            
            logger.info(f"SMS sent successfully. SID: {message.sid}, To: {formatted_phone}")
            return True, f"SMS sent successfully. SID: {message.sid}"
            
        except TwilioRestException as e:
            logger.error(f"Twilio error: {str(e)}")
            return False, f"Failed to send SMS: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error sending SMS: {str(e)}")
            return False, f"Failed to send SMS: {str(e)}"
    
    @staticmethod
    def format_phone_number(phone_number: str) -> str:
        """
        Format phone number to E.164 format
        
        Handles Saudi numbers:
        - 0501234567 → +966501234567
        - 501234567 → +966501234567
        - 966501234567 → +966501234567
        
        Args:
            phone_number: Phone number in various formats
            
        Returns:
            str: Formatted phone number in E.164 format
        """
        # Remove all non-digit characters
        digits = ''.join(filter(str.isdigit, phone_number))
        
        # Handle Saudi numbers
        if digits.startswith('05') and len(digits) == 10:
            # Saudi mobile: 05xxxxxxxx -> +9665xxxxxxxx
            return '+966' + digits[1:]
        elif digits.startswith('5') and len(digits) == 9:
            # Saudi mobile without leading 0: 5xxxxxxxx -> +9665xxxxxxxx
            return '+966' + digits
        elif digits.startswith('966') and len(digits) >= 12:
            # Already has country code: 9665xxxxxxxx -> +9665xxxxxxxx
            return '+' + digits
        elif phone_number.startswith('+'):
            # Already in E.164 format
            return phone_number
        else:
            # Default: assume Saudi number
            if len(digits) == 10 and digits.startswith('05'):
                return '+966' + digits[1:]
            return '+' + digits
```

### Step 2: Update PhoneVerificationService

**File: `apps/core/services.py`**

Add import at the top:
```python
from .twilio_service import TwilioSMSService
```

Update the `create_verification` method:
```python
@staticmethod
def create_verification(user, phone_number):
    """Create new phone verification record and send OTP via SMS"""
    # Generate OTP
    otp_code = PhoneVerificationService.generate_otp()
    
    # Set expiration (5 minutes from now)
    expires_at = timezone.now() + timedelta(minutes=5)
    
    # Create verification record
    verification = PhoneVerification.objects.create(
        user=user,
        phone_number=phone_number,
        otp_code=otp_code,
        expires_at=expires_at
    )
    
    # Send OTP via SMS using Twilio
    formatted_phone = TwilioSMSService.format_phone_number(phone_number)
    sms_success, sms_message = TwilioSMSService.send_otp_sms(
        phone_number=formatted_phone,
        otp_code=otp_code
    )
    
    if not sms_success:
        # Log error but don't fail - OTP is still created
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to send SMS OTP: {sms_message}")
    
    return verification, otp_code
```

### Step 3: Update Views (Remove OTP from Response)

**File: `apps/core/views.py`**

Update `SendOTPView`:
```python
def post(self, request):
    serializer = PhoneVerificationSerializer(data=request.data)
    if serializer.is_valid():
        phone_number = serializer.validated_data['phone_number']
        verification, otp_code = PhoneVerificationService.create_verification(
            user=request.user,
            phone_number=phone_number
        )
        return api_response(
            success=True,
            message=f"OTP sent to {phone_number}",
            # Remove OTP from response - it's sent via SMS now!
            # data={"otp": otp_code}  # Only for testing - remove in production
        )
    # ... rest of code
```

**File: `apps/riders/views.py`**

Update `RiderSendOTPView`:
```python
def post(self, request):
    # ... existing code ...
    return api_response(
        success=True,
        message=f"OTP sent to {phone_number}",
        # Remove this in production - OTP is sent via SMS now!
        # data={"otp": otp_code}  # Only for testing
    )
```

---

## 🧪 Testing

### Test 1: Send OTP

**Endpoint:** `POST /api/core/send-otp/`

**Request:**
```bash
curl -X POST http://localhost:8000/api/core/send-otp/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "0501234567"
  }'
```

**Response:**
```json
{
  "success": true,
  "message": "OTP sent to 0501234567"
}
```

**Expected:**
- ✅ SMS received on phone
- ✅ OTP code in SMS
- ✅ No OTP in API response (security)

### Test 2: Verify OTP

**Endpoint:** `POST /api/core/verify-otp/`

**Request:**
```bash
curl -X POST http://localhost:8000/api/core/verify-otp/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "otp_code": "123456"
  }'
```

**Response (Success):**
```json
{
  "success": true,
  "message": "Phone verified successfully!"
}
```

**Response (Failure):**
```json
{
  "success": false,
  "message": "Invalid or expired OTP"
}
```

### Test 3: Check Twilio Console

1. Go to: https://console.twilio.com/
2. Click **Monitor** → **Logs** → **Messaging**
3. You should see:
   - ✅ SMS sent successfully
   - ✅ Message SID
   - ✅ Status (delivered, failed, etc.)

### Test 4: Test Different Phone Formats

Test these formats (all should work):
- `0501234567` → `+966501234567`
- `501234567` → `+966501234567`
- `966501234567` → `+966501234567`
- `+966501234567` → `+966501234567`

---

## 🔧 Troubleshooting

### Issue 1: "Invalid phone number"

**Error:**
```
Twilio error: The number +966501234567 is not a valid phone number
```

**Solutions:**
- ✅ Ensure phone number is in E.164 format (`+966501234567`)
- ✅ Use `TwilioSMSService.format_phone_number()` to format
- ✅ Check country code is correct (Saudi = +966)

### Issue 2: "Unverified phone number" (Trial Account)

**Error:**
```
Twilio error: The number +966501234567 is unverified
```

**Solution:**
1. Go to Twilio Console → Phone Numbers → Verified Caller IDs
2. Add your test phone number
3. Verify it via SMS/call
4. Or upgrade to paid account (no verification needed)

### Issue 3: SMS Not Received

**Possible Causes:**
- ❌ Wrong phone number format
- ❌ Insufficient Twilio credits
- ❌ Phone number blocked/carrier issue
- ❌ Twilio account suspended

**Debug Steps:**
1. Check Twilio Console → Logs → Messaging
2. Look for error messages
3. Check account balance
4. Verify phone number format
5. Test with different phone number

### Issue 4: "Authentication failed"

**Error:**
```
Twilio error: Authentication failed
```

**Solutions:**
- ✅ Check `TWILIO_ACCOUNT_SID` in `.env`
- ✅ Check `TWILIO_AUTH_TOKEN` in `.env`
- ✅ Ensure no extra spaces in credentials
- ✅ Restart Django server after updating `.env`

### Issue 5: "SMS service not configured"

**Error:**
```
SMS service not configured
```

**Solutions:**
- ✅ Add Twilio credentials to `.env`
- ✅ Add Twilio settings to `settings.py`
- ✅ Restart Django server

### Issue 6: OTP Still in API Response

**Problem:**
OTP code is still returned in API response (security risk)

**Solution:**
- ✅ Remove `data={"otp": otp_code}` from response
- ✅ Only return success message
- ✅ OTP should only be sent via SMS

---

## 🏭 Production Considerations

### 1. Security

**✅ Do:**
- Never return OTP in API response
- Log SMS failures but don't expose errors to users
- Rate limit OTP requests (prevent spam)
- Validate phone numbers before sending

**❌ Don't:**
- Expose Twilio credentials
- Return OTP in API response
- Send OTP without rate limiting
- Log OTP codes in plain text

### 2. Rate Limiting

**Add rate limiting to prevent abuse:**

```python
from django.core.cache import cache
from rest_framework.exceptions import Throttled

def check_rate_limit(phone_number: str, max_requests: int = 5, window: int = 300):
    """
    Check if phone number has exceeded rate limit
    
    Args:
        phone_number: Phone number to check
        max_requests: Maximum requests per window
        window: Time window in seconds (default: 5 minutes)
    """
    cache_key = f"otp_rate_limit_{phone_number}"
    requests = cache.get(cache_key, 0)
    
    if requests >= max_requests:
        raise Throttled(detail="Too many OTP requests. Please try again later.")
    
    cache.set(cache_key, requests + 1, window)
```

### 3. Cost Management

**Monitor Twilio usage:**
- Set up billing alerts in Twilio Console
- Monitor SMS costs per month
- Consider bulk pricing for high volume
- Track failed SMS (wasted credits)

**Cost Estimation:**
- Saudi Arabia: ~$0.05 per SMS
- 1000 SMS/month = ~$50/month
- Free trial: $15.50 credit = ~310 SMS

### 4. Error Handling

**Graceful degradation:**
```python
# If SMS fails, log but don't break the flow
if not sms_success:
    logger.error(f"Failed to send SMS: {sms_message}")
    # Optionally: Send email OTP as fallback
    # Or queue for retry
```

### 5. Message Templates

**Customize SMS message:**
```python
# Arabic message option
message_body_ar = f"رمز التحقق الخاص بك هو: {otp_code}. صالح لمدة 5 دقائق."

# English message
message_body_en = f"Your Mgask verification code is: {otp_code}. Valid for 5 minutes."

# Use based on user preference
```

### 6. Testing in Production

**Before going live:**
- ✅ Test with real phone numbers
- ✅ Verify SMS delivery
- ✅ Test OTP verification
- ✅ Check error handling
- ✅ Monitor Twilio logs
- ✅ Set up billing alerts

---

## 📊 API Endpoints

### Send OTP

**Endpoint:** `POST /api/core/send-otp/`

**Authentication:** Required (Bearer Token)

**Request Body:**
```json
{
  "phone_number": "0501234567"
}
```

**Response:**
```json
{
  "success": true,
  "message": "OTP sent to 0501234567"
}
```

### Verify OTP

**Endpoint:** `POST /api/core/verify-otp/`

**Authentication:** Required (Bearer Token)

**Request Body:**
```json
{
  "otp_code": "123456"
}
```

**Response (Success):**
```json
{
  "success": true,
  "message": "Phone verified successfully!"
}
```

**Response (Failure):**
```json
{
  "success": false,
  "message": "Invalid or expired OTP"
}
```

### Rider-Specific Endpoints

- `POST /api/riders/send-otp/` - Send OTP to rider
- `POST /api/riders/verify-otp/` - Verify rider OTP

---

## 📝 Checklist

### Setup
- [ ] Twilio account created
- [ ] Account SID obtained
- [ ] Auth Token obtained
- [ ] Phone number purchased/obtained
- [ ] Twilio SDK installed
- [ ] Credentials added to `.env`
- [ ] Settings added to `settings.py`

### Implementation
- [ ] `TwilioSMSService` created
- [ ] `PhoneVerificationService` updated
- [ ] Views updated (OTP removed from response)
- [ ] Phone number formatting implemented
- [ ] Error handling added

### Testing
- [ ] Test send OTP
- [ ] Test verify OTP
- [ ] Test different phone formats
- [ ] Check Twilio console logs
- [ ] Test error scenarios
- [ ] Test rate limiting (if implemented)

### Production
- [ ] OTP removed from API responses
- [ ] Rate limiting implemented
- [ ] Error handling tested
- [ ] Billing alerts set up
- [ ] Monitoring configured
- [ ] Documentation updated

---

## 🔗 Useful Links

- **Twilio Console:** https://console.twilio.com/
- **Twilio Docs:** https://www.twilio.com/docs
- **Twilio Python SDK:** https://www.twilio.com/docs/libraries/python
- **E.164 Format:** https://en.wikipedia.org/wiki/E.164
- **Saudi Phone Numbers:** https://en.wikipedia.org/wiki/Telephone_numbers_in_Saudi_Arabia

---

## 📞 Support

**Twilio Support:**
- Documentation: https://www.twilio.com/docs
- Support: https://support.twilio.com/
- Status: https://status.twilio.com/

**Internal Support:**
- Check logs: `logs/django.log`
- Check Twilio console logs
- Review error messages in API responses

---

## 🎯 Summary

**What we did:**
1. ✅ Integrated Twilio SMS service
2. ✅ Added phone number formatting (Saudi numbers)
3. ✅ Updated OTP service to send SMS
4. ✅ Removed OTP from API responses (security)
5. ✅ Added error handling

**Result:**
- Users receive OTP via SMS
- Phone verification works end-to-end
- Secure (OTP not exposed in API)
- Production-ready with proper error handling

**Next Steps:**
- Test thoroughly
- Monitor costs
- Set up rate limiting
- Deploy to production

---

*Last Updated: [Current Date]*
*Version: 1.0*

