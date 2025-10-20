#!/bin/bash

# Script to find the correct service name for your Django application

echo "Searching for Django/Gunicorn services..."
echo "========================================"

# List all services that might be related to your app
echo "Services containing 'zthob', 'gunicorn', or 'django':"
systemctl list-units --type=service --all | grep -E "(zthob|gunicorn|django)" || echo "No matching services found"

echo ""
echo "All active services:"
systemctl list-units --type=service --state=active | head -20

echo ""
echo "Services in /etc/systemd/system/:"
ls -la /etc/systemd/system/ | grep -E "(zthob|gunicorn|django)" || echo "No matching service files found"

echo ""
echo "Processes running Python/Django:"
ps aux | grep -E "(python|django|gunicorn)" | grep -v grep || echo "No Python processes found"

echo ""
echo "If you find the service name, you can restart it with:"
echo "sudo systemctl restart <service-name>"
