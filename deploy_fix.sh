#!/bin/bash

# Deployment script to fix the multiple addresses issue
# This script should be run on the production server

echo "Starting deployment of address fix..."

# Navigate to the project directory
cd /home/zthob-backend

# Activate virtual environment
source magsk_venv/bin/activate

# Pull latest changes (if using git)
# git pull origin main

# Run the cleanup script for user ID 2
echo "Cleaning up duplicate addresses for user ID 2..."
python3 cleanup_addresses.py 2

# Restart the application
echo "Restarting the application..."

# Try different possible service names
if systemctl is-active --quiet zthob; then
    echo "Restarting zthob service..."
    sudo systemctl restart zthob
elif systemctl is-active --quiet zthob-backend; then
    echo "Restarting zthob-backend service..."
    sudo systemctl restart zthob-backend
elif systemctl is-active --quiet gunicorn; then
    echo "Restarting gunicorn service..."
    sudo systemctl restart gunicorn
else
    echo "No active service found. Trying to restart common service names..."
    echo "Available services:"
    systemctl list-units --type=service | grep -E "(zthob|gunicorn|django)" || echo "No matching services found"
    
    # Try to restart any service that might be running the app
    sudo systemctl restart zthob-backend 2>/dev/null || \
    sudo systemctl restart gunicorn 2>/dev/null || \
    sudo systemctl restart zthob 2>/dev/null || \
    echo "Could not restart service automatically. Please restart manually."
fi

echo "Deployment completed!"
echo "The application should now handle multiple addresses properly."
