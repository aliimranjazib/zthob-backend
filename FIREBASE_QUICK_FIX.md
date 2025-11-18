# Firebase Setup - Quick Fix for "Key Creation Restricted" Error

## What This Error Means

**Error:** "Key creation is not allowed on this service account. Please check if service account key creation is restricted by organization policies."

**Meaning:** Your Google Cloud organization has security policies that prevent downloading service account JSON keys. This is common in enterprise environments.

**Good News:** You don't need the JSON key file! There are better ways to authenticate.

---

## ✅ Quick Solution: Use Application Default Credentials

This is the **recommended** approach and works even when key creation is restricted.

### Step 1: Install Google Cloud SDK (if not installed)

```bash
# macOS
brew install google-cloud-sdk

# Or download from: https://cloud.google.com/sdk/docs/install
```

### Step 2: Authenticate

```bash
# Login with your Google account
gcloud auth application-default login

# Set your Firebase project
gcloud config set project mgask-2025
```

### Step 3: That's It! 🎉

The code already supports this! Just **don't set** `FIREBASE_CREDENTIALS_PATH` in settings.py, and Firebase will automatically use Application Default Credentials.

**Your settings.py should NOT have:**
```python
# DON'T set this if using ADC
# FIREBASE_CREDENTIALS_PATH = 'path/to/file.json'
```

**Just leave it unset**, and the code will use ADC automatically.

---

## Test It

1. **Run your Django server:**
   ```bash
   python manage.py runserver
   ```

2. **Check logs** - you should see:
   ```
   Firebase initialized using Application Default Credentials
   ```

3. **Test notifications** - they should work now!

---

## For Production (Google Cloud)

If you're deploying to:
- **Google Cloud Run**
- **Google App Engine**
- **Google Compute Engine**

Just **attach the Firebase service account** to your instance/container, and ADC will work automatically - no credentials file needed!

---

## Alternative: Test Without Firebase

If you want to test the notification system **without Firebase**:

1. **Don't configure Firebase** (leave `FIREBASE_CREDENTIALS_PATH` unset)
2. **Notifications will be logged** in the database but not sent
3. **Check notification logs:**
   ```bash
   curl 'YOUR_BASE_URL/api/notifications/logs/' \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

This lets you test the entire flow and verify notifications are being triggered correctly!

---

## Still Having Issues?

See `FIREBASE_SETUP_ALTERNATIVES.md` for:
- More detailed setup instructions
- Alternative authentication methods
- Firebase REST API approach
- Troubleshooting tips

---

## Summary

**Problem:** Can't download service account JSON key  
**Solution:** Use `gcloud auth application-default login`  
**Result:** Firebase works without any JSON file! ✅


