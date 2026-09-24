#!/usr/bin/env bash
# ==============================================================================
# Antidote Issue Tracker - Cloudflare Quick Tunnel Starter
# ==============================================================================
# Bringt die lokale Antidote-Instanz mit einem einzigen Befehl per echtem HTTPS
# online – ohne Serverkauf, ohne Router-Portfreigabe, ideal für Live-Tests.
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$ROOT_DIR"

echo "===================================================================="
echo "    ANTIDOTE ISSUE TRACKER - CLOUDFLARE LIVE TUNNEL STARTER"
echo "===================================================================="

# 1. Prüfe ob cloudflared installiert ist
if ! command -v cloudflared &> /dev/null; then
    echo ""
    echo "[!] 'cloudflared' wurde auf diesem Rechner nicht gefunden!"
    echo ""
    echo "So installierst du cloudflared in wenigen Sekunden:"
    echo ""
    echo "  -> Linux (Ubuntu / Debian):"
    echo "     curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb"
    echo "     sudo dpkg -i cloudflared.deb && rm cloudflared.deb"
    echo ""
    echo "  -> macOS (Homebrew):"
    echo "     brew install cloudflared"
    echo ""
    echo "  -> Windows (PowerShell als Admin):"
    echo "     winget install --id Cloudflare.cloudflared"
    echo ""
    echo "Installiere bitte cloudflared und starte dieses Skript danach erneut."
    exit 1
fi

# 2. Lokale Umgebung prüfen
if [ ! -x ".venv/bin/python" ]; then
    echo "[!] Python-Umgebung fehlt. Installiere zuerst die lokalen Abhängigkeiten (siehe DEPLOYMENT_GUIDE.md)." >&2
    exit 1
fi
PYTHON_BIN=".venv/bin/python"

# Der öffentliche Test läuft mit eigenem Sitzungsschlüssel und sicheren Cookies.
export DEBUG=False
export SECRET_KEY
SECRET_KEY="$("$PYTHON_BIN" -c 'import secrets; print(secrets.token_urlsafe(64))')"
export ALLOWED_HOSTS=".trycloudflare.com,127.0.0.1,localhost"
export CSRF_TRUSTED_ORIGINS="https://*.trycloudflare.com"
export USE_X_ACCEL_REDIRECT=False
export VITE_DEV_MODE=False

# 3. Prüfe und baue Frontend-Assets
if [ ! -f "static/dist/manifest.json" ]; then
    echo ">>> [1/4] Baue Frontend-Assets (Vite)..."
    npm run build
else
    echo ">>> [1/4] Frontend-Assets sind bereits gebaut (static/dist/ vorhanden)."
fi

# 4. Datenbankmigrationen prüfen
echo ">>> [2/4] Führe Datenbankmigrationen aus..."
"$PYTHON_BIN" manage.py migrate --noinput

# Demokonten haben bekannte Passwörter und dürfen nicht veröffentlicht werden.
if ! "$PYTHON_BIN" manage.py shell -c 'from django.contrib.auth import get_user_model; import sys; users=get_user_model().objects; defaults={"admin":"admin123","developer":"password123","viewer":"password123"}; sys.exit(1 if any((u := users.filter(username=name).first()) and u.check_password(password) for name,password in defaults.items()) else 0)'; then
    echo "[!] Mindestens ein Demokonto hat noch sein bekanntes Passwort. Ändere diese Passwörter vor dem Tunnel-Start." >&2
    exit 1
fi

# 5. Statische Dateien sammeln
echo ">>> [3/4] Sammle statische Dateien..."
"$PYTHON_BIN" manage.py collectstatic --noinput

# 6. Django im Hintergrund starten
PORT="${PORT:-8000}"
echo ">>> [4/4] Starte lokalen Django-Server auf Port $PORT..."

# Ein fremder Prozess auf dem Port darf nicht versehentlich veröffentlicht werden.
if "$PYTHON_BIN" -c 'import socket,sys; s=socket.socket(); result=s.connect_ex(("127.0.0.1", int(sys.argv[1]))); s.close(); sys.exit(0 if result == 0 else 1)' "$PORT"; then
    echo "[!] Port $PORT ist bereits belegt. Beende den Prozess oder wähle einen anderen PORT." >&2
    exit 1
fi
"$PYTHON_BIN" manage.py runserver --insecure --noreload "127.0.0.1:$PORT" &
SERVER_PID=$!

cleanup() {
    echo ""
    echo ">>> Beende Cloudflare Tunnel und Django-Server..."
    if [ -n "${SERVER_PID:-}" ]; then
        kill "$SERVER_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT
trap 'exit 130' SIGINT
trap 'exit 143' SIGTERM

# Warte kurz, bis Django bereit ist
sleep 2
if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "[!] Django konnte nicht gestartet werden; Tunnel wird nicht geöffnet." >&2
    exit 1
fi

echo ""
echo "===================================================================="
echo ">>> Starte Cloudflare HTTPS-Tunnel zu http://127.0.0.1:$PORT ..."
echo ">>> Gleich erscheint eine öffentliche https://*.trycloudflare.com URL!"
echo ">>> Diese URL kannst du an Kunden, Tester oder dein Handy schicken."
echo "===================================================================="
echo ""

cloudflared tunnel --url "http://127.0.0.1:$PORT"
