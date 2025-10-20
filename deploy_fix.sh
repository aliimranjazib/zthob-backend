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
sudo systemctl restart zthob

echo "Deployment completed successfully!"
echo "The application should now handle multiple addresses properly."
