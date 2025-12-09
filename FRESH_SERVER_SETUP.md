# Fresh Server Setup Guide - PostgreSQL

Complete guide to set up a fresh server with PostgreSQL database.

## Prerequisites

- Ubuntu/Debian server
- Root/SSH access
- PostgreSQL installed (or will install)

---

## Step 1: Clean Server (Delete Everything)

```bash
ssh root@69.62.126.95

# Stop all services
sudo systemctl stop gunicorn nginx 2>/dev/null || true
sudo pkill -9 gunicorn python3 2>/dev/null || true

# Delete everything
sudo rm -rf /home/zthob-backend
sudo rm -f /etc/systemd/system/gunicorn.service
sudo rm -f /etc/systemd/system/zthob.service
sudo rm -f /etc/nginx/sites-enabled/zthob
sudo rm -f /etc/nginx/sites-available/zthob
sudo systemctl daemon-reload

echo "Server cleaned!"
```

---

## Step 2: Install PostgreSQL

```bash
# Update packages
sudo apt update

# Install PostgreSQL
sudo apt install postgresql postgresql-contrib -y

# Start PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Check status
sudo systemctl status postgresql
```

---

## Step 3: Setup PostgreSQL Database

```bash
# Switch to postgres user
sudo -u postgres psql

# Inside PostgreSQL prompt, run:
CREATE DATABASE mgask;
CREATE USER mgask_user WITH PASSWORD 'mgaskapp-2025';
ALTER ROLE mgask_user SET client_encoding TO 'utf8';
ALTER ROLE mgask_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE mgask_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE mgask TO mgask_user;
\q

# Test connection
sudo -u postgres psql -d mgask -c "SELECT version();"
```

**Save the password!** You'll need it for `.env` file.

---

## Step 4: Install Python & Dependencies

```bash
# Install Python and pip
sudo apt install python3 python3-pip python3-venv -y

# Install PostgreSQL development libraries (required for psycopg2)
sudo apt install python3-dev libpq-dev -y

# Install other system dependencies
sudo apt install build-essential -y
```

---

## Step 5: Clone & Setup Project

```bash
# Create project directory
sudo mkdir -p /home/mgask-backend
sudo chown $USER:$USER /home/mgask-backend
cd /home/mgask-backend

# Clone repository
git clone https://github.com/aliimranjazib/zthob-backend.git .

git@github.com:aliimranjazib/zthob-backend.git
# OR if using SSH:
# git clone git@github.com:YOUR_USERNAME/YOUR_REPO.git .

# Create virtual environment
python3 -m venv magsk_venv
source magsk_venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

---

## Step 6: Configure Environment Variables

```bash
cd /home/mgask-backend

# Create .env file
nano .env
```

Add these variables:

```bash
# Django Settings
DJANGO_SECRET_KEY=your-secret-key-here-generate-new-one
DEBUG=False
DJANGO_ENVIRONMENT=production

# Database (PostgreSQL)
DB_NAME=mgask
DB_USER=mgask_user
DB_PASSWORD=mgask-2025
DB_HOST=localhost
DB_PORT=5432

# Allowed Hosts
DJANGO_ALLOWED_HOSTS=69.62.126.95,mgask.net,www.mgask.net

# Firebase
FIREBASE_CREDENTIALS_PATH=config/firebase-credentials.json
FIREBASE_PROJECT_ID=mgask-2025

# Twilio (if using)
TWILIO_ACCOUNT_SID=ACde6078fe8c9b33a77a869d85a0c5c60b
TWILIO_AUTH_TOKEN=2f56032189d44ad930978ae5025b5cb0
TWILIO_PHONE_NUMBER=+17252553868

# Email (if using)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password
DEFAULT_FROM_EMAIL=noreply@mgask.net
```

**Generate secret key:**
```bash
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## Step 7: Setup Firebase Credentials

```bash
cd /home/mgask-backend

# Create config directory
mkdir -p config

# Upload your firebase-credentials.json file
# Use scp from your local machine:
# scp config/firebase-credentials.json root@69.62.126.95:/home/zthob-backend/config/

# Or create it manually:
nano config/firebase-credentials.json
# Paste your Firebase service account JSON
```

---

## Step 8: Run Migrations

```bash
cd /home/mgask-backend
source magsk_venv/bin/activate

# Run migrations
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput
```

---

## Step 9: Setup Gunicorn Service

```bash
# Create service file
sudo nano /etc/systemd/system/gunicorn.service
```

Add this content:

```ini
[Unit]
Description=Mgask Django Application
After=network.target postgresql.service

[Service]
Type=notify
User=root
Group=root
WorkingDirectory=/home/mgask-backend
Environment="PATH=/home/mgask-backend/magsk_venv/bin"
Environment="DJANGO_SETTINGS_MODULE=mgask.settings"
ExecStart=/home/mgask-backend/magsk_venv/bin/gunicorn --config gunicorn.conf.py mgask.wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable gunicorn
sudo systemctl start gunicorn
sudo systemctl status gunicorn
```

---

## Step 10: Setup Nginx

```bash
# Install Nginx
sudo apt install nginx -y

# Create config
sudo nano /etc/nginx/sites-available/mgask
```

Add this:

```nginx
server {
    listen 80;
    server_name 69.62.126.95 mgask.net www.mgask.net;

    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /home/mgask-backend/staticfiles/;
    }

    location /media/ {
        alias /home/mgask-backend/media/;
    }
}
```

Enable and restart:

```bash
sudo ln -s /etc/nginx/sites-available/mgask /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/mgask
sudo nginx -t
sudo systemctl restart nginx
sudo systemctl enable nginx
```

---

## Step 11: Verify Everything

```bash
# Check services
sudo systemctl status gunicorn
sudo systemctl status nginx
sudo systemctl status postgresql

# Check logs
sudo journalctl -u gunicorn -n 50

# Test API
curl http://localhost:8000/api/config/version/
curl http://69.62.126.95/api/config/version/

# Test database
sudo -u postgres psql -d zthob -c "\dt"
```

---

## Step 12: Setup Firewall (if needed)

```bash
# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp
sudo ufw enable
```

---

## Quick Setup Script

Save this as `setup_fresh_server.sh` and run it:

```bash
#!/bin/bash
# Fresh Server Setup Script

set -e

echo "=== Fresh Server Setup ==="

# Install PostgreSQL
echo "Installing PostgreSQL..."
sudo apt update
sudo apt install -y postgresql postgresql-contrib python3 python3-pip python3-venv python3-dev libpq-dev build-essential nginx

# Setup PostgreSQL
echo "Setting up database..."
sudo -u postgres psql << EOF
CREATE DATABASE zthob;
CREATE USER zthob_user WITH PASSWORD 'CHANGE_THIS_PASSWORD';
ALTER ROLE zthob_user SET client_encoding TO 'utf8';
ALTER ROLE zthob_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE zthob_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE zthob TO zthob_user;
EOF

# Clone project
echo "Cloning project..."
cd /home
sudo rm -rf zthob-backend
sudo mkdir -p zthob-backend
sudo chown $USER:$USER zthob-backend
cd zthob-backend
git clone https://github.com/YOUR_REPO.git .

# Setup virtual environment
echo "Setting up Python environment..."
python3 -m venv magsk_venv
source magsk_venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file (you need to edit this)
echo "Creating .env file..."
cat > .env << 'ENVEOF'
DJANGO_SECRET_KEY=CHANGE_THIS
DEBUG=False
DJANGO_ENVIRONMENT=production
DB_NAME=zthob
DB_USER=zthob_user
DB_PASSWORD=CHANGE_THIS_PASSWORD
DB_HOST=localhost
DB_PORT=5432
DJANGO_ALLOWED_HOSTS=69.62.126.95,mgask.net,www.mgask.net
FIREBASE_CREDENTIALS_PATH=config/firebase-credentials.json
FIREBASE_PROJECT_ID=mgask-2025
ENVEOF

echo "⚠️  IMPORTANT: Edit .env file with correct values!"
echo "Then run: python manage.py migrate"
echo "Then setup gunicorn and nginx (see guide above)"
```

---

## After Setup

1. **Test all endpoints**
2. **Verify version endpoint**: `curl http://69.62.126.95/api/config/version/`
3. **Test deliveries endpoints**
4. **Check admin panel**: `http://69.62.126.95/admin/`
5. **Verify database**: Check tables exist in PostgreSQL

---

## Troubleshooting

### PostgreSQL Connection Error
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Check connection
sudo -u postgres psql -d zthob -c "SELECT 1;"

# Check .env file has correct DB credentials
```

### Gunicorn Not Starting
```bash
# Check logs
sudo journalctl -u gunicorn -n 50

# Check permissions
ls -la /home/zthob-backend

# Test manually
cd /home/zthob-backend
source magsk_venv/bin/activate
python manage.py check
```

### Nginx 502 Error
```bash
# Check gunicorn is running
sudo systemctl status gunicorn

# Check nginx config
sudo nginx -t

# Check logs
sudo tail -f /var/log/nginx/error.log
```

---

## Next Steps

After fresh setup, your GitHub Actions deployment will work automatically. Just push code and it will deploy!

