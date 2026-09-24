#!/usr/bin/env bash
# ==============================================================================
# Antidote Issue Tracker - Deployment & Update Script
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
    if [ "${EUID:-$(id -u)}" -eq 0 ]; then
        runuser -u antidote -- git -C "$APP_DIR" pull --ff-only
    else
        git pull --ff-only
    fi
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

DB_PATH="$DATA_DIR/db.sqlite3"
if [ ! -f "$DB_PATH" ] && [ -f "$APP_DIR/db.sqlite3" ]; then
    DB_PATH="$APP_DIR/db.sqlite3"
fi
if [ -f "$DB_PATH" ]; then
    sqlite3 "$DB_PATH" "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL; PRAGMA busy_timeout=5000;" || true
fi

# Ensure ownership if run as root
if [ "${EUID:-$(id -u)}" -eq 0 ]; then
    chown -R antidote:www-data "$APP_DIR" "$DATA_DIR" /var/www/antidote/staticfiles /var/www/antidote/media 2>/dev/null || true
    chmod -R 775 "$DATA_DIR" /var/www/antidote/media 2>/dev/null || true
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
