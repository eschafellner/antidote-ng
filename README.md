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
**Empfohlen für neue Installationen:** Docker Compose baut die App, startet Gunicorn und Caddy und verwaltet HTTPS sowie persistente Volumes für Datenbank und Uploads. Die Einrichtung und Update-Befehle stehen im [Deployment-Guide](DEPLOYMENT_GUIDE.md#empfohlen-docker-compose).

Für Domains bei Cloudflare gibt es alternativ [Docker Compose mit Cloudflare Tunnel](DEPLOYMENT_GUIDE.md#docker-compose-mit-cloudflare-tunnel). Dabei verbindet ein `cloudflared`-Container die App ohne öffentliche Server-Ports mit Cloudflare.

Das bisherige manuelle Setup mit Nginx, systemd und Certbot ist dort ebenfalls beschrieben. Bestehende Installationen benötigen für einen Wechsel zu Docker eine gesonderte Datenmigration.

Details siehe **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)**.
