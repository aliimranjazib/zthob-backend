# 🔧 Fix Twilio SMS on Production Server

## ❌ Current Issue
**Error:** `"SMS service not configured"`

This means Twilio credentials are missing on your production server.

---

## ✅ Solution: Add Twilio Credentials to Production Server

### Step 1: SSH into Production Server

```bash
ssh root@69.62.126.95
```

### Step 2: Navigate to Project Directory

```bash
cd /home/zthob-backend
```

### Step 3: Check Current .env File

```bash
cat .env | grep TWILIO
```

If you see nothing, the credentials are missing.

### Step 4: Add Twilio Credentials to .env

**Option A: Edit .env file directly**
```bash
nano .env
```

Add these lines (replace with your actual Twilio credentials):
```bash
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE_NUMBER=+17252553868
```

**Option B: Append to .env file**
```bash
echo "" >> .env
echo "# Twilio SMS Configuration" >> .env
echo "TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" >> .env
echo "TWILIO_AUTH_TOKEN=your_auth_token_here" >> .env
echo "TWILIO_PHONE_NUMBER=+17252553868" >> .env
```

### Step 5: Verify Credentials Were Added

```bash
cat .env | grep TWILIO
```

You should see:
```
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=+17252553868
```

### Step 6: Install python-dotenv (if not already installed)

The code now loads .env automatically, but we need python-dotenv:

```bash
source magsk_venv/bin/activate
pip3 install python-dotenv
```

### Step 7: Restart Gunicorn Service

```bash
sudo systemctl restart gunicorn
```

### Step 8: Verify Service is Running

```bash
sudo systemctl status gunicorn
```

### Step 9: Test Again

Try sending OTP from your Flutter app again. You should now see:
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

---

## 🔍 Where to Get Twilio Credentials

1. **Go to Twilio Console:** https://console.twilio.com/
2. **Account SID:** Found on dashboard (starts with `AC...`)
3. **Auth Token:** Click "show" button next to Auth Token on dashboard
4. **Phone Number:** Your Twilio phone number (already have: `+17252553868`)

---

## 🚨 Important Notes

1. **Restart Required:** After adding .env variables, you MUST restart gunicorn
2. **python-dotenv:** Make sure it's installed so Django can load .env file
3. **File Permissions:** Make sure .env file is readable by the Django process
4. **Trial Account:** If using trial account, verify phone numbers in Twilio Console

---

## 🧪 Quick Test Script

After adding credentials, test directly on server:

```bash
cd /home/zthob-backend
source magsk_venv/bin/activate
python3 manage.py shell
```

Then in Python shell:
```python
from django.conf import settings
print("TWILIO_ACCOUNT_SID:", "✅ SET" if settings.TWILIO_ACCOUNT_SID else "❌ NOT SET")
print("TWILIO_AUTH_TOKEN:", "✅ SET" if settings.TWILIO_AUTH_TOKEN else "❌ NOT SET")
print("TWILIO_PHONE_NUMBER:", settings.TWILIO_PHONE_NUMBER or "❌ NOT SET")

# Test SMS service
from apps.core.twilio_service import TwilioSMSService
success, message = TwilioSMSService.send_otp_sms("+17252553868", "123456")
print(f"\nSMS Test: {'✅ SUCCESS' if success else '❌ FAILED'}")
print(f"Message: {message}")
```

---

## 📋 Checklist

- [ ] SSH into production server
- [ ] Navigate to `/home/zthob-backend`
- [ ] Add `TWILIO_ACCOUNT_SID` to .env
- [ ] Add `TWILIO_AUTH_TOKEN` to .env
- [ ] Add `TWILIO_PHONE_NUMBER` to .env
- [ ] Verify credentials in .env file
- [ ] Install python-dotenv (`pip3 install python-dotenv`)
- [ ] Restart gunicorn (`sudo systemctl restart gunicorn`)
- [ ] Test API again from Flutter app
- [ ] Check response for `"sms_sent": true`

---

## 🆘 Still Not Working?

1. **Check logs:**
   ```bash
   tail -100 /home/zthob-backend/logs/django.log | grep -i twilio
   ```

2. **Check if python-dotenv is installed:**
   ```bash
   source magsk_venv/bin/activate
   pip3 list | grep dotenv
   ```

3. **Verify .env file exists and is readable:**
   ```bash
   ls -la /home/zthob-backend/.env
   cat /home/zthob-backend/.env | grep TWILIO
   ```

4. **Check Twilio Console:** https://console.twilio.com/ → Monitor → Logs → Messaging

