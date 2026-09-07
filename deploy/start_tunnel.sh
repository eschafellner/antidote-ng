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

# 2. Prüfe Python-Umgebung
PYTHON_BIN="python3"
if [ -d ".venv" ]; then
    PYTHON_BIN=".venv/bin/python"
elif command -v python &> /dev/null; then
    PYTHON_BIN="python"
fi

# 3. Prüfe und baue Frontend-Assets
if [ ! -f "static/dist/manifest.json" ]; then
    echo ">>> [1/4] Baue Frontend-Assets (Vite)..."
    if command -v npm &> /dev/null; then
        npm run build
    else
        echo "[!] npm wurde nicht gefunden. Bitte führe 'npm run build' aus!"
    fi
else
    echo ">>> [1/4] Frontend-Assets sind bereits gebaut (static/dist/ vorhanden)."
fi

# 4. Datenbankmigrationen prüfen
echo ">>> [2/4] Führe Datenbankmigrationen aus..."
"$PYTHON_BIN" manage.py migrate --noinput

# 5. Statische Dateien sammeln
echo ">>> [3/4] Sammle statische Dateien..."
"$PYTHON_BIN" manage.py collectstatic --noinput

# 6. Django im Hintergrund starten
PORT="${PORT:-8000}"
echo ">>> [4/4] Starte lokalen Django-Server auf Port $PORT..."

# Prüfe, ob Port belegt ist
if lsof -Pi :"$PORT" -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo ">>> Hinweis: Auf Port $PORT läuft bereits ein Prozess. Nutze vorhandenen Server."
    SERVER_PID=""
else
    "$PYTHON_BIN" manage.py runserver --insecure "127.0.0.1:$PORT" &
    SERVER_PID=$!
fi

cleanup() {
    echo ""
    echo ">>> Beende Cloudflare Tunnel und Django-Server..."
    if [ -n "${SERVER_PID:-}" ]; then
        kill "$SERVER_PID" 2>/dev/null || true
    fi
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# Warte kurz, bis Django bereit ist
sleep 2

echo ""
echo "===================================================================="
echo ">>> Starte Cloudflare HTTPS-Tunnel zu http://127.0.0.1:$PORT ..."
echo ">>> Gleich erscheint eine öffentliche https://*.trycloudflare.com URL!"
echo ">>> Diese URL kannst du an Kunden, Tester oder dein Handy schicken."
echo "===================================================================="
echo ""

cloudflared tunnel --url "http://127.0.0.1:$PORT"
