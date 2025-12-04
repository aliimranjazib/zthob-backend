# Fix Firebase Credentials Issue

The Firebase credentials path is not persisting because the systemd service doesn't have access to the `.env` file. Here's how to fix it:

## Problem
- Firebase credentials work initially but stop working after some time
- Error: "Firebase not configured. Set FIREBASE_CREDENTIALS_PATH in .env..."
- This happens because systemd services don't automatically load `.env` files

## Solution

### Option 1: Set Environment Variables in Systemd Service (Recommended)

**1. Check the current systemd service file:**
```bash
sudo cat /etc/systemd/system/gunicorn.service
```

**2. Edit the service file to include environment variables:**
```bash
sudo nano /etc/systemd/system/gunicorn.service
```

**3. Add Environment variables in the `[Service]` section:**
```ini
[Service]
# ... existing configuration ...
Environment="FIREBASE_CREDENTIALS_PATH=/home/zthob-backend/config/firebase-credentials.json"
Environment="FIREBASE_PROJECT_ID=mgask-2025"
Environment="DJANGO_ENVIRONMENT=production"
# Add any other environment variables from .env that you need
```

**4. Reload systemd and restart the service:**
```bash
sudo systemctl daemon-reload
sudo systemctl restart gunicorn
sudo systemctl status gunicorn
```

### Option 2: Use Absolute Path in .env File

**1. Make sure your `.env` file uses an absolute path:**
```bash
cd /home/zthob-backend
nano .env
```

**2. Set the absolute path (not relative):**
```env
FIREBASE_CREDENTIALS_PATH=/home/zthob-backend/config/firebase-credentials.json
FIREBASE_PROJECT_ID=mgask-2025
```

**3. Verify the file exists:**
```bash
ls -la /home/zthob-backend/config/firebase-credentials.json
```

**4. Restart gunicorn:**
```bash
sudo systemctl restart gunicorn
```

### Option 3: Load .env File in WSGI (Alternative)

If you can't modify the systemd service, you can load the .env file in `zthob/wsgi.py`:

```python
import os
from django.core.wsgi import get_wsgi_application

# Load .env file before Django setup
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / '.env')
except ImportError:
    pass

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zthob.settings')

application = get_wsgi_application()
```

## Verify the Fix

**1. Test Firebase configuration:**
```bash
cd /home/zthob-backend
source magsk_venv/bin/activate
python3 manage.py test_firebase
```

**2. Check if environment variables are loaded:**
```bash
cd /home/zthob-backend
source magsk_venv/bin/activate
python3 manage.py shell -c "from django.conf import settings; print('Firebase Path:', settings.FIREBASE_CREDENTIALS_PATH); print('Project ID:', settings.FIREBASE_PROJECT_ID)"
```

**3. Test sending a notification:**
```bash
curl -X POST http://localhost:8000/api/notifications/test/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json"
```

## Troubleshooting

**If credentials still don't work:**

1. **Check file permissions:**
   ```bash
   ls -la /home/zthob-backend/config/firebase-credentials.json
   sudo chmod 644 /home/zthob-backend/config/firebase-credentials.json
   ```

2. **Check if the path is correct:**
   ```bash
   python3 -c "import os; print('Path exists:', os.path.exists('/home/zthob-backend/config/firebase-credentials.json'))"
   ```

3. **Check systemd environment:**
   ```bash
   sudo systemctl show gunicorn | grep Environment
   ```

4. **Check gunicorn logs:**
   ```bash
   sudo journalctl -u gunicorn -n 50 --no-pager | grep -i firebase
   ```

5. **Verify the JSON file is valid:**
   ```bash
   python3 -c "import json; json.load(open('/home/zthob-backend/config/firebase-credentials.json')); print('Valid JSON')"
   ```

## Quick Fix Script

Run this on the server to automatically fix the systemd service:

```bash
#!/bin/bash
# Fix Firebase credentials in systemd service

SERVICE_FILE="/etc/systemd/system/gunicorn.service"
CRED_PATH="/home/zthob-backend/config/firebase-credentials.json"

# Check if service file exists
if [ ! -f "$SERVICE_FILE" ]; then
    echo "Service file not found: $SERVICE_FILE"
    exit 1
fi

# Check if credentials file exists
if [ ! -f "$CRED_PATH" ]; then
    echo "Credentials file not found: $CRED_PATH"
    exit 1
fi

# Backup service file
sudo cp "$SERVICE_FILE" "${SERVICE_FILE}.backup"

# Add environment variables if not present
if ! grep -q "FIREBASE_CREDENTIALS_PATH" "$SERVICE_FILE"; then
    # Add after [Service] line
    sudo sed -i '/\[Service\]/a Environment="FIREBASE_CREDENTIALS_PATH='"$CRED_PATH"'"' "$SERVICE_FILE"
    sudo sed -i '/FIREBASE_CREDENTIALS_PATH/a Environment="FIREBASE_PROJECT_ID=mgask-2025"' "$SERVICE_FILE"
    echo "Added Firebase environment variables to service file"
else
    echo "Firebase environment variables already present"
fi

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart gunicorn
sudo systemctl status gunicorn
```

Save this as `fix_firebase.sh`, make it executable, and run it:
```bash
chmod +x fix_firebase.sh
sudo ./fix_firebase.sh
```

