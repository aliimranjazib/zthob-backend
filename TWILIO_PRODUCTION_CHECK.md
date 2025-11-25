# Twilio SMS Production Server Check

## 🔍 Quick Diagnostic Steps

### Step 1: Check Server Logs

SSH into your production server and check Django logs:

```bash
# SSH to server
ssh root@69.62.126.95

# Check Django logs for SMS errors
tail -100 /home/zthob-backend/logs/django.log | grep -i "sms\|twilio"

# Or check gunicorn logs
journalctl -u gunicorn --since "10 minutes ago" | grep -i "sms\|twilio"
```

**Look for:**
- ✅ `SMS sent successfully. SID: ...` - SMS was sent
- ❌ `Failed to send SMS OTP` - SMS failed
- ❌ `Twilio not configured` - Credentials missing
- ❌ `Twilio error: ...` - Twilio API error

### Step 2: Verify Twilio Credentials on Server

```bash
# SSH to server
ssh root@69.62.126.95
cd /home/zthob-backend

# Check if .env file exists and has Twilio credentials
cat .env | grep TWILIO

# Or check environment variables
source magsk_venv/bin/activate
python3 manage.py shell
```

In Django shell:
```python
from django.conf import settings
print("TWILIO_ACCOUNT_SID:", "SET" if settings.TWILIO_ACCOUNT_SID else "NOT SET")
print("TWILIO_AUTH_TOKEN:", "SET" if settings.TWILIO_AUTH_TOKEN else "NOT SET")
print("TWILIO_PHONE_NUMBER:", settings.TWILIO_PHONE_NUMBER or "NOT SET")
```

### Step 3: Verify Twilio SDK is Installed

```bash
# SSH to server
ssh root@69.62.126.95
cd /home/zthob-backend
source magsk_venv/bin/activate

# Check if twilio is installed
pip3 list | grep twilio

# If not installed, install it
pip3 install twilio
```

### Step 4: Check API Response

After the update, the API will now return SMS status:

**Success Response:**
```json
{
  "success": true,
  "message": "OTP sent to +17252553868",
  "data": {
    "sms_sent": true,
    "sms_message": "SMS sent successfully"
  }
}
```

**Failure Response:**
```json
{
  "success": true,
  "message": "OTP generated for +17252553868, but SMS sending failed. Please check server logs.",
  "data": {
    "sms_sent": false,
    "sms_message": "Failed to send SMS: [error details]"
  }
}
```

### Step 5: Check Twilio Console

1. Go to: https://console.twilio.com/
2. Navigate to: **Monitor** → **Logs** → **Messaging**
3. Check for recent messages:
   - ✅ **Delivered** - SMS was sent and delivered
   - ⏳ **Queued** - SMS is queued for delivery
   - ❌ **Failed** - SMS failed (check error message)

### Step 6: Common Issues & Solutions

#### Issue 1: "Twilio not configured"
**Solution:**
```bash
# Add to .env file on server
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE_NUMBER=+17252553868

# Restart gunicorn
sudo systemctl restart gunicorn
```

#### Issue 2: "ModuleNotFoundError: No module named 'twilio'"
**Solution:**
```bash
source magsk_venv/bin/activate
pip3 install twilio
sudo systemctl restart gunicorn
```

#### Issue 3: "The number +17252553868 is unverified"
**Solution:**
- If using Twilio trial account, verify the number:
  1. Go to Twilio Console → Phone Numbers → Verified Caller IDs
  2. Click "Add a new Caller ID"
  3. Enter phone number and verify via SMS/call

#### Issue 4: "Insufficient Twilio credits"
**Solution:**
- Check Twilio Console → Billing
- Add credits or upgrade account

### Step 7: Test SMS Sending Directly

SSH to server and run:

```bash
cd /home/zthob-backend
source magsk_venv/bin/activate
python3 manage.py shell
```

```python
from apps.core.twilio_service import TwilioSMSService

# Test SMS sending
success, message = TwilioSMSService.send_otp_sms(
    phone_number="+17252553868",
    otp_code="123456"
)

print(f"Success: {success}")
print(f"Message: {message}")
```

---

## 📋 Production Deployment Checklist

- [ ] Twilio credentials added to `.env` on production server
- [ ] Twilio SDK installed (`pip3 install twilio`)
- [ ] Environment variables loaded (restart gunicorn after adding .env)
- [ ] Phone number verified in Twilio Console (if trial account)
- [ ] Server logs checked for SMS errors
- [ ] API response includes SMS status
- [ ] Twilio Console shows message logs

---

## 🚀 Quick Fix Commands

```bash
# 1. SSH to server
ssh root@69.62.126.95

# 2. Navigate to project
cd /home/zthob-backend

# 3. Activate virtual environment
source magsk_venv/bin/activate

# 4. Install Twilio (if not installed)
pip3 install twilio

# 5. Add credentials to .env (if missing)
echo "TWILIO_ACCOUNT_SID=ACxxxxx" >> .env
echo "TWILIO_AUTH_TOKEN=xxxxx" >> .env
echo "TWILIO_PHONE_NUMBER=+17252553868" >> .env

# 6. Restart gunicorn
sudo systemctl restart gunicorn

# 7. Check logs
tail -f /home/zthob-backend/logs/django.log
```

---

## 📞 Need Help?

1. **Check server logs** - Most errors are logged there
2. **Check Twilio Console** - See message delivery status
3. **Check API response** - Now includes SMS status
4. **Verify credentials** - Make sure all 3 Twilio variables are set

