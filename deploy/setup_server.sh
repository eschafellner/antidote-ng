#!/usr/bin/env bash
# ==============================================================================
# Antidote Issue Tracker - One-Shot Server Setup for GCP e2-micro (Ubuntu 26.04)
# ==============================================================================
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
   echo "Error: This script must be run as root (e.g. sudo bash setup_server.sh)" 1>&2
   exit 1
fi

echo ">>> [1/7] Updating system packages..."
apt update && apt upgrade -y
apt install -y curl git ufw fail2ban certbot python3-certbot-nginx \
    python3-pip python3-venv build-essential sqlite3 libsqlite3-dev nginx

echo ">>> [2/7] Configuring 2GB Swap space (Prevents OOM on 1GB RAM)..."
if [[ ! -f /swapfile ]]; then
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

# Kernel memory tuning for low-RAM machines
cat << 'SYSCTL' > /etc/sysctl.d/99-antidote.conf
vm.swappiness=10
vm.vfs_cache_pressure=50
SYSCTL
sysctl --system

echo ">>> [3/7] Installing Node.js LTS (v22)..."
if ! command -v node &> /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
    apt install -y nodejs
fi

echo ">>> [4/7] Creating system user & directories..."
id -u antidote &>/dev/null || useradd --system --shell /bin/bash --home /var/www/antidote antidote
mkdir -p /var/www/antidote/app \
         /var/www/antidote/data \
         /var/www/antidote/media \
         /var/www/antidote/staticfiles \
         /var/log/antidote \
         /run/antidote

chown -R antidote:www-data /var/www/antidote /var/log/antidote /run/antidote
chmod -R 775 /var/www/antidote/data /var/www/antidote/media

echo ">>> [5/7] Installing Systemd Service..."
cat << 'SERVICE' > /etc/systemd/system/antidote.service
[Unit]
Description=Antidote Issue Tracker (Gunicorn WSGI)
After=network.target

[Service]
Type=notify
User=antidote
Group=www-data
WorkingDirectory=/var/www/antidote/app
RuntimeDirectory=antidote
ExecStart=/var/www/antidote/venv/bin/gunicorn \
    --workers 2 \
    --threads 2 \
    --worker-class gthread \
    --worker-tmp-dir /dev/shm \
    --bind unix:/run/antidote/gunicorn.sock \
    --timeout 30 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --access-logfile /var/log/antidote/access.log \
    --error-logfile /var/log/antidote/error.log \
    config.wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=10
PrivateTmp=true
Restart=always
RestartSec=5s

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload

echo ">>> [6/7] Configuring Nginx..."
cat << 'NGINX' > /etc/nginx/sites-available/antidote
upstream antidote_app {
    server unix:/run/antidote/gunicorn.sock fail_timeout=0;
}

server {
    listen 80;
    listen [::]:80;
    server_name _;

    client_max_body_size 15M;

    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied any;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/json application/xml image/svg+xml;

    location /static/ {
        alias /var/www/antidote/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, max-age=2592000, immutable";
        access_log off;
    }

    # Protected Media Storage (Served only via authenticated Django X-Accel-Redirect)
    location /protected_media/ {
        internal;
        alias /var/www/antidote/media/;
    }

    location / {
        proxy_pass http://antidote_app;
        proxy_http_version 1.1;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        proxy_read_timeout 60s;
        proxy_connect_timeout 10s;
    }
}
NGINX

ln -sf /etc/nginx/sites-available/antidote /etc/nginx/sites-enabled/antidote
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

echo ">>> [7/7] Configuring Firewall (UFW)..."
ufw allow OpenSSH || true
ufw allow 'Nginx Full' || true
ufw --force enable || true

echo "===================================================================="
echo ">>> Server setup completed successfully!"
echo "Next steps:"
echo "1. Clone your repo into /var/www/antidote/app:"
echo "   sudo -u antidote git clone <YOUR_GIT_URL> /var/www/antidote/app"
echo "2. Create /var/www/antidote/app/.env with DEBUG=False & SECRET_KEY"
echo "3. Run deployment script: bash /var/www/antidote/app/deploy.sh"
echo "4. Obtain SSL certificate:"
echo "   sudo certbot --nginx -d YOUR_DOMAIN.com"
echo "===================================================================="
