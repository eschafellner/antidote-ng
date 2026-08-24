#!/usr/bin/env bash
# ==============================================================================
# Antidote Issue Tracker - Zero-Downtime Deployment & Update Script
# ==============================================================================
set -euo pipefail

APP_DIR="${APP_DIR:-/var/www/antidote/app}"
VENV_DIR="${VENV_DIR:-/var/www/antidote/venv}"
DATA_DIR="${DATA_DIR:-/var/www/antidote/data}"

echo "=========================================="
echo ">>> Starting Antidote Deployment..."
echo "=========================================="

cd "$APP_DIR"

# 1. Pull latest changes if git repo is present
if [ -d ".git" ]; then
    echo ">>> [1/6] Pulling latest git commits..."
    git pull origin main || git pull || echo "Git pull skipped or failed, continuing..."
fi

# 2. Virtual Environment & Python dependencies
echo ">>> [2/6] Updating Python dependencies..."
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi
"$VENV_DIR/bin/pip" install --upgrade pip --quiet
"$VENV_DIR/bin/pip" install -r requirements.txt --quiet

# 3. Node.js & Frontend Build (Memory constrained)
echo ">>> [3/6] Building frontend assets..."
npm ci --silent
NODE_OPTIONS="--max-old-space-size=512" npm run build

# 4. Collect static files
echo ">>> [4/6] Collecting static files..."
"$VENV_DIR/bin/python" manage.py collectstatic --noinput

# 5. Database migrations & SQLite WAL Mode
echo ">>> [5/6] Running database migrations..."
"$VENV_DIR/bin/python" manage.py migrate --noinput

if [ -f "$DATA_DIR/db.sqlite3" ]; then
    sqlite3 "$DATA_DIR/db.sqlite3" "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL; PRAGMA busy_timeout=5000;" || true
fi

# 6. Graceful reload of Gunicorn WSGI workers
echo ">>> [6/6] Reloading application server..."
if systemctl is-active --quiet antidote; then
    systemctl reload antidote
    echo ">>> Antidote service reloaded successfully."
else
    systemctl enable --now antidote
    echo ">>> Antidote service started successfully."
fi

echo "=========================================="
echo ">>> Deployment completed successfully!"
echo "=========================================="
