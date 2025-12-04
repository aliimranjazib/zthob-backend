# Deployment Fix - Code Not Updating Issue

## Problem Identified

Your deployment pipeline was succeeding but new code wasn't appearing because of several issues:

### Issues Found:

1. **`preload_app = True` in gunicorn.conf.py**
   - This loads the app into memory before workers fork
   - Old code can remain in memory even after restart
   - **FIXED**: Changed to `preload_app = False`

2. **Python cache files not cleared**
   - `__pycache__` directories contain old compiled Python files
   - Old `.pyc` files can be used instead of new code
   - **FIXED**: Added cache clearing step in deploy.yml

3. **Service not fully killed**
   - Gunicorn processes might still be running with old code
   - **FIXED**: Added `pkill -9 gunicorn` to kill all processes

4. **No verification of new code**
   - No check to verify new files actually exist
   - **FIXED**: Added verification step for new app directories

5. **Missing migrations check**
   - New app tables not verified
   - **FIXED**: Added deliveries app tables to verification

## Changes Made

### 1. Updated `.github/workflows/deploy.yml`

**Added:**
- ✅ Clear Python cache (`__pycache__`, `.pyc` files)
- ✅ Verify latest commit is pulled
- ✅ Kill all gunicorn processes before restart
- ✅ Verify new app files exist
- ✅ Check for new database tables
- ✅ Longer wait times for service restart
- ✅ API endpoint verification

### 2. Updated `gunicorn.conf.py`

**Changed:**
- ✅ `preload_app = False` (was `True`)
  - This ensures new code is loaded on restart
  - Slight performance trade-off but ensures code updates work

## How to Deploy Now

### Option 1: Push Changes (Recommended)

```bash
# Commit the fixed files
git add .github/workflows/deploy.yml gunicorn.conf.py
git commit -m "Fix deployment: clear cache, kill processes, verify code"
git push origin main
```

The GitHub Actions workflow will automatically:
1. Pull latest code
2. Clear Python cache
3. Install dependencies
4. Run migrations
5. Kill all old processes
6. Restart service
7. Verify deployment

### Option 2: Manual Deployment (If Needed)

If you need to deploy manually right now:

```bash
ssh root@69.62.126.95

cd /home/zthob-backend

# Pull latest code
git fetch origin
git reset --hard origin/main

# Clear Python cache (CRITICAL!)
find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true

# Activate venv
source magsk_venv/bin/activate

# Install dependencies
pip3 install -r requirements.txt --upgrade

# Run migrations
python3 manage.py migrate

# Collect static files
python3 manage.py collectstatic --noinput

# CRITICAL: Kill all gunicorn processes
sudo pkill -9 gunicorn
sudo systemctl stop gunicorn

# Remove PID file
sudo rm -f /var/run/gunicorn/zthob.pid

# Wait
sleep 3

# Start service
sudo systemctl start gunicorn

# Verify
sleep 5
sudo systemctl status gunicorn
```

## Verification Steps

After deployment, verify the new code is live:

### 1. Check Service Status
```bash
sudo systemctl status gunicorn
```

### 2. Check Logs
```bash
tail -f /home/zthob-backend/logs/gunicorn_error.log
```

### 3. Test New Endpoints
```bash
# Test delivery tracking endpoint
curl http://localhost:8000/api/deliveries/customer/orders/1/tracking/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 4. Check Swagger UI
Visit: `http://your-domain.com/api/schema/swagger-ui/`

Look for:
- "Rider Delivery Tracking" section
- "Customer Delivery Tracking" section
- "Admin Delivery Tracking" section

### 5. Verify Database Tables
```bash
python3 manage.py showmigrations deliveries
```

Should show:
```
deliveries
 [X] 0001_initial
```

## Why This Happened

### Root Cause: `preload_app = True`

When `preload_app = True`:
1. Gunicorn loads your Django app into the **parent process** memory
2. Then it forks worker processes from that parent
3. When you restart, the **parent process** might still have old code
4. New workers fork from the parent, so they get old code too

**Solution**: Set `preload_app = False`
- Each worker loads the app independently
- On restart, all workers get fresh code
- Slight performance cost (app loaded per worker) but ensures updates work

### Python Cache Files

Python compiles `.py` files to `.pyc` bytecode for speed. If cache isn't cleared:
- Old `.pyc` files might be used
- New code changes might not be picked up

**Solution**: Clear cache before deployment

## Performance Note

Setting `preload_app = False` has a small performance impact:
- **Before**: App loaded once, shared by all workers (faster startup)
- **After**: App loaded per worker (slightly slower startup, but ensures updates work)

For most applications, the difference is negligible and the reliability is worth it.

## Monitoring

After deployment, monitor:

1. **Service logs**: Check for errors
   ```bash
   tail -f /home/zthob-backend/logs/gunicorn_error.log
   ```

2. **Service status**: Ensure it's running
   ```bash
   sudo systemctl status gunicorn
   ```

3. **API responses**: Test endpoints return expected data

4. **Database**: Verify new tables exist
   ```bash
   python3 manage.py showmigrations
   ```

## Future Deployments

Now that the workflow is fixed, future deployments should work automatically:

1. Push code to `main` branch
2. GitHub Actions runs automatically
3. Code is pulled, cache cleared, service restarted
4. New code is live!

## Troubleshooting

If deployment still fails:

1. **Check GitHub Actions logs**
   - Go to GitHub → Actions tab
   - Click on the failed workflow
   - Check error messages

2. **SSH into server and check**
   ```bash
   ssh root@69.62.126.95
   cd /home/zthob-backend
   git log -1  # Check if latest commit is there
   ls -la apps/deliveries/  # Check if new app exists
   ```

3. **Check service logs**
   ```bash
   sudo journalctl -u gunicorn -n 50
   ```

4. **Manual restart if needed**
   ```bash
   sudo systemctl restart gunicorn
   ```

## Summary

✅ **Fixed Issues:**
- Python cache clearing
- Gunicorn process killing
- Code verification
- Database table verification
- `preload_app` setting

✅ **Next Steps:**
1. Commit and push the fixed files
2. Watch GitHub Actions workflow
3. Verify new endpoints are available
4. Test delivery tracking feature

The deployment should now work correctly! 🚀

