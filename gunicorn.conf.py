# Gunicorn configuration file for Zthob Django app
import multiprocessing
import os

# Server socket
bind = "127.0.0.1:8000"  # Listen on localhost port 8000 (Nginx will proxy to this)
backlog = 2048           # Maximum number of pending connections

# Worker processes
# For VPS with limited resources, use fewer workers
workers = min(multiprocessing.cpu_count() * 2 + 1, 4)  # Max 4 workers for VPS
worker_class = "sync"                                   # Use sync workers for Django
worker_connections = 1000                              # Max connections per worker
timeout = 30                                           # Worker timeout in seconds
keepalive = 2                                          # Keep-alive connections

# Restart workers after this many requests, to help prevent memory leaks
max_requests = 1000
max_requests_jitter = 50

# Logging
# Use project-specific log directory
log_dir = "/home/admin/web/mgask.net/logs"
accesslog = os.path.join(log_dir, "gunicorn_access.log")
errorlog = os.path.join(log_dir, "gunicorn_error.log")
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "zthob"

# Server mechanics
daemon = False          # Don't run as daemon (systemd will manage this)
pidfile = "/var/run/gunicorn/zthob.pid"
user = "admin"          # Run as admin user
group = "admin"         # Run as admin group
tmp_upload_dir = None   # Use system default

# Preload application for better performance
preload_app = True

# Worker lifecycle
def when_ready(server):
    """Called just after the server is started."""
    server.log.info("Zthob Django app is ready to serve requests")

def worker_int(worker):
    """Called just after a worker has been forked."""
    worker.log.info("Worker spawned (pid: %s)", worker.pid)

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    server.log.info("Worker will be spawned")

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info("Worker spawned (pid: %s)", worker.pid)

# SSL (if needed - usually handled by Nginx)
# keyfile = "/path/to/keyfile"
# certfile = "/path/to/certfile"
