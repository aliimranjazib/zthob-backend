# Quick Fix: Server Not Showing Deliveries Endpoints

## Problem
The server is running old code - Django URL patterns don't include `api/deliveries/`

## Solution: Deploy Latest Code

### Option 1: Trigger GitHub Actions Deployment (Recommended)

1. **Make sure all changes are committed:**
   ```bash
   git status
   git add .
   git commit -m "Add deliveries app and fix deployment"
   git push origin main
   ```

2. **Check GitHub Actions:**
   - Go to: https://github.com/your-repo/actions
   - Wait for deployment to complete
   - Check logs for errors

### Option 2: Manual Deployment via SSH

**Quick SSH deployment:**

```bash
ssh root@69.62.126.95

cd /home/zthob-backend

# Pull latest code
git fetch origin
git reset --hard origin/main

# Verify deliveries app exists
ls -la apps/deliveries/

# Verify URLs are in urls.py
grep "api/deliveries" zthob/urls.py

# Clear cache
find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Activate venv and install dependencies
source magsk_venv/bin/activate
pip3 install -r requirements.txt --upgrade

# Run migrations
python3 manage.py migrate deliveries

# Collect static
python3 manage.py collectstatic --noinput

# Restart service
sudo pkill -9 gunicorn
sudo systemctl stop gunicorn
sleep 3
sudo systemctl start gunicorn
sleep 5

# Verify
systemctl status gunicorn
curl http://localhost:8000/api/schema/
```

### Option 3: Use the Deployment Script

Run the script I created:

```bash
./manual_deploy_deliveries.sh
```

## Verify Deployment

After deployment, test:

```bash
# Should return 200 or 401 (not 404)
curl http://69.62.126.95/api/deliveries/admin/orders/1/tracking/route

# Check Swagger UI
# Visit: http://69.62.126.95/api/schema/swagger-ui/
# Look for "Delivery Tracking" sections
```

## What to Check

1. **Is deliveries app on server?**
   ```bash
   ssh root@69.62.126.95 "ls -la /home/zthob-backend/apps/deliveries/"
   ```

2. **Are URLs in urls.py?**
   ```bash
   ssh root@69.62.126.95 "grep 'api/deliveries' /home/zthob-backend/zthob/urls.py"
   ```

3. **Is app in INSTALLED_APPS?**
   ```bash
   ssh root@69.62.126.95 "grep 'apps.deliveries' /home/zthob-backend/zthob/settings.py"
   ```

4. **Are migrations run?**
   ```bash
   ssh root@69.62.126.95 "cd /home/zthob-backend && source magsk_venv/bin/activate && python3 manage.py showmigrations deliveries"
   ```

## Most Likely Issue

The server code is outdated. The deployment workflow might have:
- Failed silently
- Not pulled latest code
- Not restarted service properly

**Quick fix:** SSH in and manually pull/restart (Option 2 above)

