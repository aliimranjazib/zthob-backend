#!/bin/bash

# Deployment script for Zthob Django app
# Run this script on your VPS after cloning from GitHub

set -e  # Exit on any error

echo "Starting deployment of Zthob Django app..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="zthob"
PROJECT_DIR="/home/admin/web/mgask.net/public_html"
VENV_DIR="/home/admin/web/mgask.net/venv"
DOMAIN="mgask.net"
GITHUB_REPO="https://github.com/aliimranjazib/zthob-backend.git"

echo -e "${YELLOW}Step 1: Cloning repository from GitHub...${NC}"
cd /home/admin/web/$DOMAIN
if [ -d "public_html" ]; then
    echo "Backing up existing public_html..."
    mv public_html public_html_backup_$(date +%Y%m%d_%H%M%S)
fi
git clone $GITHUB_REPO public_html
cd public_html

echo -e "${YELLOW}Step 2: Creating virtual environment...${NC}"
cd /home/admin/web/$DOMAIN
python3 -m venv venv
source venv/bin/activate

echo -e "${YELLOW}Step 3: Installing dependencies...${NC}"
pip install --upgrade pip
pip install -r requirements.production.txt

echo -e "${YELLOW}Step 4: Setting up environment variables...${NC}"
cp env.production .env

echo -e "${YELLOW}Step 5: Collecting static files...${NC}"
python manage.py collectstatic --noinput

echo -e "${YELLOW}Step 6: Running database migrations...${NC}"
python manage.py migrate

echo -e "${YELLOW}Step 7: Creating superuser (if needed)...${NC}"
echo "You may need to create a superuser manually:"
echo "python manage.py createsuperuser"

echo -e "${GREEN}Deployment completed successfully!${NC}"
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Configure Nginx"
echo "2. Set up Gunicorn service"
echo "3. Configure SSL certificate"
echo "4. Test your application"
