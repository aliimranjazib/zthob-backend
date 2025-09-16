# Git-Based Deployment Guide for Zthob Django App

## 🎯 Overview
This guide will help you deploy your Django app from GitHub to your Hostinger VPS with HestiaCP.

**Repository**: [https://github.com/aliimranjazib/zthob-backend](https://github.com/aliimranjazib/zthob-backend)
**Domain**: mgask.net
**VPS IP**: 69.62.126.95

## 🚀 Quick Deployment Steps

### **Step 1: Connect to Your VPS**
```bash
ssh admin@69.62.126.95
```

### **Step 2: Install Git (if not already installed)**
```bash
sudo apt update
sudo apt install -y git
```

### **Step 3: Clone Your Repository**
```bash
cd /home/admin/web/mgask.net
git clone https://github.com/aliimranjazib/zthob-backend.git public_html
cd public_html
```

### **Step 4: Run the Deployment Script**
```bash
# Make the script executable
chmod +x deploy.sh

# Run the deployment
bash deploy.sh
```

## 📋 Detailed Deployment Process

### **Step 1: Initial VPS Setup**

#### 1.1 Connect to VPS
```bash
ssh admin@69.62.126.95
```

#### 1.2 Update system packages
```bash
sudo apt update && sudo apt upgrade -y
```

#### 1.3 Install required packages
```bash
sudo apt install -y python3 python3-pip python3-venv python3-dev
sudo apt install -y postgresql postgresql-contrib
sudo apt install -y nginx git
```

### **Step 2: Database Setup**

#### 2.1 Configure PostgreSQL
```bash
sudo -u postgres psql
```

In PostgreSQL shell:
```sql
CREATE DATABASE zthob_prod;
CREATE USER zthob_user WITH PASSWORD 'zthob123';
GRANT ALL PRIVILEGES ON DATABASE zthob_prod TO zthob_user;
ALTER USER zthob_user CREATEDB;
\q
```

#### 2.2 Configure PostgreSQL for Django
```bash
sudo nano /etc/postgresql/*/main/postgresql.conf
```
Find and uncomment:
```
listen_addresses = 'localhost'
```

```bash
sudo nano /etc/postgresql/*/main/pg_hba.conf
```
Add this line:
```
local   all             zthob_user                            md5
```

Restart PostgreSQL:
```bash
sudo systemctl restart postgresql
```

### **Step 3: Clone and Setup Project**

#### 3.1 Clone from GitHub
```bash
cd /home/admin/web/mgask.net
git clone https://github.com/aliimranjazib/zthob-backend.git public_html
cd public_html
```

#### 3.2 Create virtual environment
```bash
cd /home/admin/web/mgask.net
python3 -m venv venv
source venv/bin/activate
```

#### 3.3 Install dependencies
```bash
pip install --upgrade pip
pip install -r requirements.production.txt
```

#### 3.4 Setup environment variables
```bash
cp env.production .env
nano .env
```

**Important**: Generate a new Django secret key:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Update the `.env` file with the new secret key.

### **Step 4: Django Configuration**

#### 4.1 Collect static files
```bash
python manage.py collectstatic --noinput
```

#### 4.2 Run database migrations
```bash
python manage.py migrate
```

#### 4.3 Create superuser
```bash
python manage.py createsuperuser
```

#### 4.4 Test the application
```bash
python manage.py runserver 0.0.0.0:8000
```

### **Step 5: Configure Gunicorn**

#### 5.1 Create log directories
```bash
sudo mkdir -p /var/log/gunicorn
sudo chown admin:admin /var/log/gunicorn
sudo mkdir -p /var/run/gunicorn
sudo chown admin:admin /var/run/gunicorn
```

#### 5.2 Copy systemd service file
```bash
sudo cp zthob.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable zthob
sudo systemctl start zthob
sudo systemctl status zthob
```

### **Step 6: Configure Nginx**

#### 6.1 Using HestiaCP (Recommended)
1. Login to HestiaCP: `https://69.62.126.95:8083`
2. Go to **Web** → **mgask.net**
3. Click **Edit** next to Nginx configuration
4. Replace the content with the provided `nginx.conf`
5. Save and restart Nginx

#### 6.2 Manual Nginx configuration
```bash
sudo nano /home/admin/conf/web/nginx.mgask.net.conf
```
Paste the content from `nginx.conf`.

### **Step 7: SSL Certificate**

#### 7.1 Using HestiaCP
1. Go to **Web** → **mgask.net**
2. Click **SSL Certificate**
3. Select **Let's Encrypt**
4. Enable **Force HTTPS**
5. Click **Save**

### **Step 8: Final Configuration**

#### 8.1 Set proper permissions
```bash
sudo chown -R admin:admin /home/admin/web/mgask.net
sudo chmod -R 755 /home/admin/web/mgask.net/public_html
```

#### 8.2 Create logs directory
```bash
mkdir -p /home/admin/web/mgask.net/logs
```

#### 8.3 Restart services
```bash
sudo systemctl restart zthob
sudo systemctl restart nginx
```

## 🔄 Updating Your App

### **Method 1: Manual Update**
```bash
cd /home/admin/web/mgask.net/public_html
git pull origin main
source ../venv/bin/activate
pip install -r requirements.production.txt
python manage.py collectstatic --noinput
python manage.py migrate
sudo systemctl restart zthob
```

### **Method 2: Automated Update Script**
Create an update script:
```bash
nano /home/admin/web/mgask.net/update.sh
```

Add this content:
```bash
#!/bin/bash
cd /home/admin/web/mgask.net/public_html
git pull origin main
source ../venv/bin/activate
pip install -r requirements.production.txt
python manage.py collectstatic --noinput
python manage.py migrate
sudo systemctl restart zthob
echo "Update completed!"
```

Make it executable:
```bash
chmod +x /home/admin/web/mgask.net/update.sh
```

## 🧪 Testing Your Deployment

### **Test 1: Check Services**
```bash
sudo systemctl status zthob
sudo systemctl status nginx
sudo systemctl status postgresql
```

### **Test 2: Check Logs**
```bash
# Gunicorn logs
sudo journalctl -u zthob -f

# Nginx logs
sudo tail -f /var/log/nginx/error.log

# Application logs
tail -f /home/admin/web/mgask.net/logs/gunicorn_access.log
```

### **Test 3: Test Endpoints**
- **Admin**: `https://mgask.net/admin/`
- **API Docs**: `https://mgask.net/api/schema/swagger-ui/`
- **API**: `https://mgask.net/api/`

## 🛠️ Troubleshooting

### **Common Issues:**

#### **1. 502 Bad Gateway**
```bash
# Check if Gunicorn is running
sudo systemctl status zthob

# Check logs
sudo journalctl -u zthob -f

# Restart service
sudo systemctl restart zthob
```

#### **2. Static Files Not Loading**
```bash
# Collect static files
python manage.py collectstatic --noinput

# Check Nginx configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
```

#### **3. Database Connection Errors**
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Test database connection
psql -U zthob_user -h localhost -d zthob_prod
```

#### **4. Permission Errors**
```bash
# Fix ownership
sudo chown -R admin:admin /home/admin/web/mgask.net

# Fix permissions
sudo chmod -R 755 /home/admin/web/mgask.net/public_html
```

## 📊 Monitoring Commands

### **Check System Resources**
```bash
# CPU and Memory
htop

# Disk usage
df -h

# Network connections
netstat -tlnp | grep :8000
```

### **Check Application Status**
```bash
# Gunicorn processes
ps aux | grep gunicorn

# Memory usage
ps aux | grep gunicorn | awk '{sum+=$6} END {print sum/1024 " MB"}'

# Active connections
netstat -an | grep :8000 | wc -l
```

## 🔒 Security Checklist

- [ ] Change default SSH port
- [ ] Set up firewall (UFW)
- [ ] Use strong passwords
- [ ] Enable fail2ban
- [ ] Regular security updates
- [ ] Backup database regularly
- [ ] Monitor logs

## 💾 Backup Strategy

### **Database Backup**
```bash
pg_dump -U zthob_user -h localhost zthob_prod > backup_$(date +%Y%m%d_%H%M%S).sql
```

### **Files Backup**
```bash
tar -czf zthob_backup_$(date +%Y%m%d_%H%M%S).tar.gz /home/admin/web/mgask.net
```

## 🎯 Your Access Points

- **SSH**: `ssh admin@69.62.126.95`
- **HestiaCP**: `https://69.62.126.95:8083`
- **Your App**: `https://mgask.net`
- **GitHub**: [https://github.com/aliimranjazib/zthob-backend](https://github.com/aliimranjazib/zthob-backend)

## 🆘 Getting Help

1. **Check logs** first: `sudo journalctl -u zthob -f`
2. **Test configuration**: `sudo nginx -t`
3. **Check service status**: `sudo systemctl status zthob`
4. **Review this guide** for troubleshooting steps

Your Django app should now be successfully deployed and accessible at `https://mgask.net`! 🎉
