#!/bin/bash
# Manual deployment script for deliveries feature
# Run this if GitHub Actions deployment isn't working

echo "=========================================="
echo "Manual Deployment Script for Deliveries"
echo "=========================================="

# Server details
SERVER="root@69.62.126.95"
PROJECT_DIR="/home/zthob-backend"

echo ""
echo "Step 1: Pulling latest code..."
ssh $SERVER "cd $PROJECT_DIR && git fetch origin && git reset --hard origin/main && git log -1 --oneline"

echo ""
echo "Step 2: Verifying deliveries app exists..."
ssh $SERVER "cd $PROJECT_DIR && ls -la apps/deliveries/ 2>/dev/null || echo 'ERROR: deliveries app not found!'"

echo ""
echo "Step 3: Checking if deliveries URLs are in urls.py..."
ssh $SERVER "cd $PROJECT_DIR && grep -q 'api/deliveries' zthob/urls.py && echo 'SUCCESS: URLs found' || echo 'ERROR: URLs not found!'"

echo ""
echo "Step 4: Clearing Python cache..."
ssh $SERVER "cd $PROJECT_DIR && find . -type d -name '__pycache__' -exec rm -r {} + 2>/dev/null || true && find . -type f -name '*.pyc' -delete 2>/dev/null || true && echo 'Cache cleared'"

echo ""
echo "Step 5: Activating virtual environment and installing dependencies..."
ssh $SERVER "cd $PROJECT_DIR && source magsk_venv/bin/activate && pip3 install -r requirements.txt --upgrade --quiet"

echo ""
echo "Step 6: Running migrations..."
ssh $SERVER "cd $PROJECT_DIR && source magsk_venv/bin/activate && python3 manage.py migrate deliveries --verbosity=1"

echo ""
echo "Step 7: Collecting static files..."
ssh $SERVER "cd $PROJECT_DIR && source magsk_venv/bin/activate && python3 manage.py collectstatic --noinput"

echo ""
echo "Step 8: Restarting service..."
ssh $SERVER "sudo systemctl stop gunicorn || true && sudo pkill -9 gunicorn || true && sleep 3 && sudo systemctl start gunicorn && sleep 5 && sudo systemctl status gunicorn --no-pager"

echo ""
echo "Step 9: Verifying service is running..."
ssh $SERVER "systemctl is-active gunicorn && echo 'SUCCESS: Service is running!' || echo 'ERROR: Service failed to start!'"

echo ""
echo "Step 10: Testing endpoint..."
ssh $SERVER "curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/api/schema/ && echo ' - API is responding' || echo ' - API not responding'"

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""
echo "Test the endpoint:"
echo "curl http://69.62.126.95/api/deliveries/admin/orders/1/tracking/route"
echo ""

