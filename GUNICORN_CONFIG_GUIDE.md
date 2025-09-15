# Complete Gunicorn Configuration Guide

## 🎯 What is Gunicorn?

Gunicorn (Green Unicorn) is a Python WSGI HTTP Server for UNIX. It's a pre-fork worker model, meaning it spawns multiple worker processes to handle requests.

## 📋 Configuration Options Explained

### **1. Server Socket Settings**

```python
bind = "127.0.0.1:8000"
```
- **What it does**: Tells Gunicorn which IP and port to listen on
- **127.0.0.1**: Only listen on localhost (secure, Nginx will proxy to this)
- **8000**: Port number (can be changed if needed)
- **Alternative**: `bind = "unix:/tmp/gunicorn.sock"` (Unix socket)

```python
backlog = 2048
```
- **What it does**: Maximum number of pending connections
- **Default**: 2048 (usually fine)
- **For high traffic**: Increase to 4096 or 8192

### **2. Worker Process Settings**

```python
workers = min(multiprocessing.cpu_count() * 2 + 1, 4)
```
- **Formula**: CPU cores × 2 + 1
- **For VPS**: Limited to 4 workers to save memory
- **For dedicated server**: Can use full formula
- **Example**: 2 CPU cores = 5 workers, but limited to 4

```python
worker_class = "sync"
```
- **sync**: Standard synchronous workers (good for Django)
- **gevent**: Asynchronous workers (good for I/O heavy apps)
- **eventlet**: Another async option
- **For Django**: Usually stick with "sync"

```python
timeout = 30
```
- **What it does**: How long a worker can take to process a request
- **Default**: 30 seconds
- **For slow APIs**: Increase to 60 or 120
- **For fast APIs**: Can decrease to 15

### **3. Memory Management**

```python
max_requests = 1000
max_requests_jitter = 50
```
- **max_requests**: Restart worker after 1000 requests (prevents memory leaks)
- **max_requests_jitter**: Random variation (950-1050 requests)
- **Purpose**: Prevents all workers restarting at the same time

### **4. Logging Configuration**

```python
log_dir = "/home/admin/web/yourdomain.com/logs"
accesslog = os.path.join(log_dir, "gunicorn_access.log")
errorlog = os.path.join(log_dir, "gunicorn_error.log")
loglevel = "info"
```

**Log Levels**:
- `debug`: Very verbose (development only)
- `info`: Standard information (recommended)
- `warning`: Only warnings and errors
- `error`: Only errors

**Log Format**:
```
%(h)s - Remote address
%(l)s - Remote logname
%(u)s - Remote user
%(t)s - Time of request
%(r)s - Request line
%(s)s - Status code
%(b)s - Response size
%(f)s - Referer
%(a)s - User agent
%(D)s - Request duration in microseconds
```

## 🔧 Configuration for Different Scenarios

### **For Small VPS (1-2 CPU cores, 1-2GB RAM)**
```python
workers = 2
worker_connections = 500
timeout = 30
max_requests = 500
```

### **For Medium VPS (2-4 CPU cores, 4-8GB RAM)**
```python
workers = 4
worker_connections = 1000
timeout = 30
max_requests = 1000
```

### **For High Traffic (4+ CPU cores, 8GB+ RAM)**
```python
workers = multiprocessing.cpu_count() * 2 + 1
worker_connections = 2000
timeout = 60
max_requests = 2000
```

### **For Development/Testing**
```python
workers = 1
timeout = 120
loglevel = "debug"
reload = True  # Auto-reload on code changes
```

## 🚀 Performance Optimization

### **1. Preload Application**
```python
preload_app = True
```
- **What it does**: Loads the Django app before forking workers
- **Benefit**: Saves memory and startup time
- **Use when**: You have enough RAM

### **2. Worker Class Selection**

**Sync Workers (Default)**:
```python
worker_class = "sync"
```
- Good for: CPU-bound tasks, standard Django apps
- Memory usage: Lower
- Concurrency: Limited by number of workers

**Gevent Workers**:
```python
worker_class = "gevent"
worker_connections = 1000
```
- Good for: I/O-bound tasks, many concurrent connections
- Memory usage: Higher
- Concurrency: Much higher

### **3. Memory Optimization**
```python
max_requests = 1000
max_requests_jitter = 50
preload_app = True
```

## 🛠️ Troubleshooting Common Issues

### **Issue 1: Workers Dying Frequently**
```python
# Increase timeout
timeout = 60

# Increase max requests
max_requests = 2000

# Add worker restart settings
max_requests_jitter = 100
```

### **Issue 2: High Memory Usage**
```python
# Reduce workers
workers = 2

# Disable preload
preload_app = False

# Lower max requests
max_requests = 500
```

### **Issue 3: Slow Response Times**
```python
# Increase workers
workers = 6

# Use gevent workers
worker_class = "gevent"
worker_connections = 1000

# Increase timeout
timeout = 60
```

### **Issue 4: Connection Refused**
```python
# Check bind address
bind = "127.0.0.1:8000"  # Make sure this matches Nginx config

# Check if port is available
# Run: netstat -tlnp | grep :8000
```

## 📊 Monitoring and Logs

### **Check Gunicorn Status**
```bash
sudo systemctl status zthob
sudo journalctl -u zthob -f
```

### **View Logs**
```bash
# Access logs
tail -f /home/admin/web/yourdomain.com/logs/gunicorn_access.log

# Error logs
tail -f /home/admin/web/yourdomain.com/logs/gunicorn_error.log
```

### **Monitor Performance**
```bash
# Check worker processes
ps aux | grep gunicorn

# Check memory usage
ps aux | grep gunicorn | awk '{sum+=$6} END {print sum/1024 " MB"}'

# Check connections
netstat -an | grep :8000 | wc -l
```

## 🔒 Security Considerations

### **1. Run as Non-Root User**
```python
user = "admin"
group = "admin"
```

### **2. Bind to Localhost Only**
```python
bind = "127.0.0.1:8000"  # Not 0.0.0.0:8000
```

### **3. Set Proper Permissions**
```bash
chmod 600 gunicorn.conf.py
chown admin:admin gunicorn.conf.py
```

## 📝 Example Configurations

### **Minimal Configuration**
```python
bind = "127.0.0.1:8000"
workers = 2
timeout = 30
accesslog = "/var/log/gunicorn/access.log"
errorlog = "/var/log/gunicorn/error.log"
```

### **Production Configuration**
```python
bind = "127.0.0.1:8000"
workers = 4
worker_class = "sync"
timeout = 30
keepalive = 2
max_requests = 1000
max_requests_jitter = 50
preload_app = True
accesslog = "/var/log/gunicorn/access.log"
errorlog = "/var/log/gunicorn/error.log"
loglevel = "info"
user = "admin"
group = "admin"
```

### **High Performance Configuration**
```python
bind = "127.0.0.1:8000"
workers = 8
worker_class = "gevent"
worker_connections = 1000
timeout = 60
keepalive = 2
max_requests = 2000
max_requests_jitter = 100
preload_app = True
accesslog = "/var/log/gunicorn/access.log"
errorlog = "/var/log/gunicorn/error.log"
loglevel = "info"
```

## 🎯 Quick Start Commands

### **Test Configuration**
```bash
# Test config file syntax
gunicorn --check-config -c gunicorn.conf.py zthob.wsgi:application

# Run with config file
gunicorn -c gunicorn.conf.py zthob.wsgi:application
```

### **Start as Service**
```bash
# Copy service file
sudo cp zthob.service /etc/systemd/system/

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable zthob
sudo systemctl start zthob

# Check status
sudo systemctl status zthob
```

Your Gunicorn configuration is now optimized for your VPS setup! The key changes I made:

1. **Limited workers** to 4 maximum (good for VPS)
2. **Added proper logging** to your project directory
3. **Set user/group** to admin
4. **Added lifecycle hooks** for better monitoring
5. **Enabled preload** for better performance

Would you like me to explain any specific part in more detail or help you customize it further for your specific VPS resources?
