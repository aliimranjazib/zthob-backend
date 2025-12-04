# Manual Deployment Instructions for Rider Test Notification

The server is running old code. Follow these steps to deploy manually:

## Option 1: SSH into Server and Deploy Manually

```bash
# 1. SSH into the server
ssh root@69.62.126.95

# 2. Navigate to project directory
cd /home/zthob-backend

# 3. Pull latest code
git fetch origin
git reset --hard origin/main

# 4. Activate virtual environment
source magsk_venv/bin/activate

# 5. Install any new dependencies (if needed)
pip3 install -r requirements.txt

# 6. Run migrations (if any)
python3 manage.py migrate

# 7. Collect static files
python3 manage.py collectstatic --noinput

# 8. Restart gunicorn service
sudo systemctl stop gunicorn
sudo rm -f /var/run/gunicorn/zthob.pid
sudo systemctl start gunicorn

# 9. Verify service is running
sudo systemctl status gunicorn

# 10. Test the endpoint
curl -X POST http://localhost:8000/api/notifications/test-rider/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Option 2: Check GitHub Actions Deployment

1. Go to your GitHub repository
2. Click on "Actions" tab
3. Check if the latest deployment workflow completed successfully
4. If it failed, check the logs to see what went wrong
5. If it succeeded but the endpoint still doesn't work, the service might need a manual restart

## Option 3: Trigger New Deployment

If the deployment failed, you can trigger a new one by:

```bash
# Make an empty commit to trigger deployment
git commit --allow-empty -m "Trigger deployment - rider notification endpoint"
git push origin main
```

## Verify Deployment

After deployment, verify the endpoint is available:

```bash
curl -X POST http://69.62.126.95/api/notifications/test-rider/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json"
```

Expected response (if working):
```json
{
  "success": true,
  "message": "Test notification sent successfully! Check your device.",
  "data": {
    "user": "rider_username",
    "fcm_tokens_count": 1
  }
}
```

