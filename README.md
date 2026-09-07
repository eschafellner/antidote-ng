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
Bringe deine lokale Instanz mit einem Befehl per HTTPS ins Internet, um fachliche Abläufe mit Testern live zu teilen:
```bash
./deploy/start_tunnel.sh
```

### 3. Produktions-Deployment auf eigenem Linux-VPS (mit HTTPS)
Vollständige Produktions-Infrastruktur mit Nginx, Gunicorn, systemd und Let's Encrypt SSL:
1. **Server-Setup (einmalig):** `sudo bash deploy/setup_server.sh meinedomain.de`
2. **Updates deployen:** `sudo bash deploy.sh`
3. **SSL aktivieren:** `sudo certbot --nginx -d meinedomain.de`

Details siehe **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)**.
