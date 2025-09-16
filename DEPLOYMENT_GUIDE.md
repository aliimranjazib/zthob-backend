# Complete Deployment Guide: Django App to Hostinger VPS with HestiaCP

## Prerequisites
- Hostinger VPS with HestiaCP installed
- Domain name pointing to your VPS IP
- SSH access to your VPS
- Basic terminal knowledge

## Step 1: Initial VPS Setup

### 1.1 Connect to your VPS
```bash
ssh root@69.62.126.95

```

### 1.2 Update system packages
```bash
sudo apt update && sudo apt upgrade -y
```

### 1.3 Install required packages
```bash
sudo apt install -y python3 python3-pip python3-venv python3-dev
sudo apt install -y postgresql postgresql-contrib
sudo apt install -y nginx
sudo apt install -y git
```

## Step 2: Database Setup

### 2.1 Configure PostgreSQL
```bash
sudo -u postgres psql
```

In PostgreSQL shell:
```sql
CREATE DATABASE zthob_prod;
CREATE USER zthob_user WITH PASSWORD '@Mgaskapp007';
GRANT ALL PRIVILEGES ON DATABASE zthob_prod TO zthob_user;
ALTER USER zthob_user CREATEDB;
\q
```

### 2.2 Configure PostgreSQL for Django
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

## Step 3: Upload Your Code

### 3.1 Method 1: Using Git (Recommended)
```bash
cd /home/admin/web/yourdomain.com
git clone https://github.com/yourusername/zthob-backend.git public_html
```

### 3.2 Method 2: Using SCP/SFTP
From your local machine:
```bash
scp -r /path/to/your/project admin@your-vps-ip:/home/admin/web/yourdomain.com/public_html
```

### 3.3 Method 3: Using HestiaCP File Manager
1. Login to HestiaCP
2. Go to File Manager
3. Navigate to `/home/admin/web/yourdomain.com/`
4. Upload your project files to `public_html` folder

## Step 4: Environment Setup

### 4.1 Create virtual environment
```bash
cd /home/admin/web/yourdomain.com
python3 -m venv venv
source venv/bin/activate
```

### 4.2 Install dependencies
```bash
pip install --upgrade pip
pip install -r requirements.production.txt
```

### 4.3 Configure environment variables
```bash
cp env.production .env
nano .env
```

Update the following in `.env`:
- `DJANGO_SECRET_KEY`: Generate a new secret key
- `DJANGO_ALLOWED_HOSTS`: Your domain name
- `DB_PASSWORD`: Your PostgreSQL password
- `CORS_ALLOWED_ORIGINS`: Your domain with https

### 4.4 Generate Django secret key
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## Step 5: Django Configuration

### 5.1 Collect static files
```bash
python manage.py collectstatic --noinput
```

### 5.2 Run database migrations
```bash
python manage.py migrate
```

### 5.3 Create superuser
```bash
python manage.py createsuperuser
```

### 5.4 Test the application
```bash
python manage.py runserver 0.0.0.0:8000
```

## Step 6: Configure Gunicorn

### 6.1 Create log directories
```bash
sudo mkdir -p /var/log/gunicorn
sudo chown admin:admin /var/log/gunicorn
sudo mkdir -p /var/run/gunicorn
sudo chown admin:admin /var/run/gunicorn
```

### 6.2 Copy systemd service file
```bash
sudo cp zthob.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable zthob
sudo systemctl start zthob
sudo systemctl status zthob
```

## Step 7: Configure Nginx

### 7.1 Using HestiaCP (Recommended)
1. Login to HestiaCP
2. Go to Web → yourdomain.com
3. Click "Edit" next to Nginx configuration
4. Replace the content with the provided `nginx.conf`
5. Update `yourdomain.com` with your actual domain
6. Save and restart Nginx

### 7.2 Manual Nginx configuration
```bash
sudo nano /home/admin/conf/web/nginx.yourdomain.com.conf
```
Paste the content from `nginx.conf` and update domain names.

## Step 8: SSL Certificate

### 8.1 Using HestiaCP
1. Go to Web → yourdomain.com
2. Click "SSL Certificate"
3. Select "Let's Encrypt"
4. Enable "Force HTTPS"
5. Click "Save"

## Step 9: Final Configuration

### 9.1 Set proper permissions
```bash
sudo chown -R admin:admin /home/admin/web/yourdomain.com
sudo chmod -R 755 /home/admin/web/yourdomain.com/public_html
```

### 9.2 Create logs directory
```bash
mkdir -p /home/admin/web/yourdomain.com/logs
```

### 9.3 Restart services
```bash
sudo systemctl restart zthob
sudo systemctl restart nginx
```

## Step 10: Testing

### 10.1 Check service status
```bash
sudo systemctl status zthob
sudo systemctl status nginx
```

### 10.2 Test your application
- Visit `https://yourdomain.com/admin/`
- Visit `https://yourdomain.com/api/schema/swagger-ui/`
- Test your API endpoints

## Troubleshooting

### Common Issues:

1. **502 Bad Gateway**
   - Check if Gunicorn is running: `sudo systemctl status zthob`
   - Check logs: `sudo journalctl -u zthob -f`

2. **Static files not loading**
   - Run: `python manage.py collectstatic --noinput`
   - Check Nginx configuration for static file paths

3. **Database connection errors**
   - Verify PostgreSQL is running: `sudo systemctl status postgresql`
   - Check database credentials in `.env`

4. **Permission errors**
   - Fix ownership: `sudo chown -R admin:admin /home/admin/web/yourdomain.com`

### Useful Commands:

```bash
# View Gunicorn logs
sudo journalctl -u zthob -f

# View Nginx logs
sudo tail -f /var/log/nginx/error.log

# Restart services
sudo systemctl restart zthob
sudo systemctl restart nginx

# Check port usage
sudo netstat -tlnp | grep :8000
```

## Security Checklist

- [ ] Change default SSH port
- [ ] Set up firewall (UFW)
- [ ] Use strong passwords
- [ ] Enable fail2ban
- [ ] Regular security updates
- [ ] Backup database regularly
- [ ] Monitor logs

## Backup Strategy

### Database backup:
```bash
pg_dump -U zthob_user -h localhost zthob_prod > backup_$(date +%Y%m%d_%H%M%S).sql
```

### Files backup:
```bash
tar -czf zthob_backup_$(date +%Y%m%d_%H%M%S).tar.gz /home/admin/web/yourdomain.com
```

## Maintenance

### Regular tasks:
1. Update system packages: `sudo apt update && sudo apt upgrade`
2. Update Python packages: `pip install --upgrade -r requirements.production.txt`
3. Backup database and files
4. Monitor logs for errors
5. Check disk space: `df -h`

Your Django app should now be successfully deployed and accessible at `https://yourdomain.com`!
