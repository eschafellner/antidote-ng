#!/usr/bin/env bash
# ==============================================================================
# Antidote Issue Tracker - Lokaler Schnellstarter (Development & Preview)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PYTHON_BIN="python3"
if [ -d ".venv" ]; then
    PYTHON_BIN=".venv/bin/python"
fi

show_help() {
    echo "Verwendung: ./run_local.sh [OPTION]"
    echo ""
    echo "Optionen:"
    echo "  --dev        (Standard) Startet Django und Vite mit Hot Module Reloading (HMR)"
    echo "  --preview    Baut das Frontend und startet Django im Produktions-Vorschaumodus"
    echo "  --seed       Führt Datenbankmigrationen aus und lädt Demo-Daten"
    echo "  --help       Zeigt diese Hilfe an"
    exit 0
}

MODE="dev"
SEED_DATA=false

for arg in "$@"; do
    case "$arg" in
        --dev) MODE="dev" ;;
        --preview) MODE="preview" ;;
        --seed) SEED_DATA=true ;;
        --help|-h) show_help ;;
    esac
done

echo "===================================================================="
echo "    ANTIDOTE ISSUE TRACKER - LOKALER TESTSERVER ($MODE)"
echo "===================================================================="

# 1. Virtuelle Umgebung prüfen
if [ ! -d ".venv" ]; then
    echo ">>> Erstelle virtuelle Umgebung (.venv)..."
    python3 -m venv .venv
    .venv/bin/pip install --upgrade pip --quiet
    .venv/bin/pip install -r requirements.txt --quiet
fi

# 2. Node Modules prüfen
if [ ! -d "node_modules" ]; then
    echo ">>> Installiere npm-Pakete..."
    npm install
fi

# 3. Datenbank vorbereiten
echo ">>> Wende Datenbankmigrationen an..."
"$PYTHON_BIN" manage.py migrate --noinput

if [ "$SEED_DATA" = true ] || [ ! -f "db.sqlite3" ]; then
    echo ">>> Lade Demo-Daten..."
    "$PYTHON_BIN" manage.py seed_demo_data || true
fi

cleanup() {
    echo ""
    echo ">>> Beende lokale Server..."
    kill 0 2>/dev/null || true
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

if [ "$MODE" = "preview" ]; then
    echo ">>> Baue Frontend-Assets (Production Bundle)..."
    npm run build
    echo ">>> Sammle statische Dateien..."
    "$PYTHON_BIN" manage.py collectstatic --noinput
    echo ""
    echo "===================================================================="
    echo ">>> Antidote läuft im Preview-Modus unter: http://127.0.0.1:8000"
    echo ">>> Login: admin / admin123 (falls Demo-Daten geladen wurden)"
    echo "===================================================================="
    "$PYTHON_BIN" manage.py runserver --insecure 127.0.0.1:8000
else
    # Dev-Modus: Vite HMR + Django
    echo ">>> Starte Vite Dev-Server (Port 5173)..."
    VITE_DEV_MODE=True npm run dev &

    sleep 1

    echo ">>> Starte Django Backend (Port 8000)..."
    echo ""
    echo "===================================================================="
    echo ">>> Antidote läuft im Dev-Modus unter: http://127.0.0.1:8000"
    echo ">>> Vite HMR läuft unter: http://127.0.0.1:5173"
    echo ">>> Login: admin / admin123 (falls Demo-Daten geladen wurden)"
    echo "===================================================================="
    VITE_DEV_MODE=True "$PYTHON_BIN" manage.py runserver 127.0.0.1:8000
fi
