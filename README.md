# Antidote (NextGen Issue-Tracker)

Leichtgewichtiger, performanter Issue-Tracker als schlanke Jira-Alternative.

## Tech-Stack
- **Backend:** Python 3.12+, Django 6.x, Inertia.js (`inertia-django`)
- **Frontend:** Vue 3, Tailwind CSS 3.x, Vite, VueDraggable
- **Datenbank:** SQLite mit WAL-Modus (oder PostgreSQL)

## Lokale Entwicklung
1. Virtuelle Umgebung erstellen und Abhängigkeiten installieren:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   npm install
   ```
2. Frontend & Backend starten:
   ```bash
   npm run dev
   python manage.py runserver
   ```
3. Demo-Daten laden (optional):
   ```bash
   python manage.py seed_demo_data
   ```

## Deployment (GCP e2-micro / Ubuntu 26.04 Minimal)
Detaillierte Deployment-Skripte und Konfigurationen liegen im Ordner [`deploy/`](./deploy):
1. **Server-Setup (einmalig):** `sudo bash deploy/setup_server.sh`
2. **Updates deployen:** `bash deploy.sh`
