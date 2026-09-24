# Antidote (NextGen Issue-Tracker)

Leichtgewichtiger, performanter Issue-Tracker als schlanke Jira-Alternative.

## Tech-Stack
- **Backend:** Python 3.12+, Django 6.x, Inertia.js (`inertia-django`)
- **Frontend:** Vue 3, Tailwind CSS 3.x, Vite, VueDraggable
- **Datenbank:** SQLite mit WAL-Modus (oder PostgreSQL)

## Schnelleinstieg & Betrieb

Ausführliche, einsteigerfreundliche Schritt-für-Schritt-Anleitungen findest du im **[Deployment- & Betriebsguide](DEPLOYMENT_GUIDE.md)**.

### 1. Lokaler Entwicklungs- & Testserver
```bash
./run_local.sh --dev --seed
```
Öffne anschließend [http://127.0.0.1:8000](http://127.0.0.1:8000) (Login: `admin` / `admin123`).

### 2. Sofort online testen via Cloudflare Tunnel (Ohne Server)
Teile eine lokale Testinstanz per HTTPS. Installiere zuvor `cloudflared`, richte die lokale Umgebung ein und ändere alle Demo-Passwörter; Details stehen im Deployment-Guide.
```bash
./deploy/start_tunnel.sh
```

### 3. Produktions-Deployment auf eigenem Linux-VPS (mit HTTPS)
Produktions-Infrastruktur mit Nginx, Gunicorn, systemd und Let's Encrypt SSL. Auf dem VPS sind nacheinander erforderlich: Git installieren und Repository klonen, `deploy/setup_server.sh` ausführen, `.env` anlegen, `deploy.sh` starten und HTTPS mit Certbot aktivieren. Die genauen Befehle und die Reihenfolge stehen im Guide.

Details siehe **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)**.
