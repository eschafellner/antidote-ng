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

### 3. Dauerhaftes Deployment mit Docker

Für eine Domain bei Cloudflare läuft Antidote wie EntailsNG mit einer `.env`-Datei und einem Compose-Befehl. Richte zuerst im Cloudflare-Dashboard einen Tunnel mit dem öffentlichen Hostnamen und der Service-URL `http://app:8000` ein. Kopiere dann `deploy/docker.env.example` nach `.env` und trage `DOMAIN`, einen neu erzeugten `SECRET_KEY` sowie `TUNNEL_TOKEN` ein. Die vollständigen Schritte stehen im [Deployment-Guide](DEPLOYMENT_GUIDE.md#docker-mit-cloudflare-tunnel).

```bash
docker compose up -d --build
docker compose exec app python manage.py createsuperuser
```

Für einen VPS mit direkten Ports 80/443 kannst du in `.env` `COMPOSE_FILE=compose.yaml` setzen; dann übernimmt Caddy das HTTPS-Zertifikat. Docker speichert Datenbank und Uploads in persistenten Volumes. Das bisherige manuelle Setup mit Nginx, systemd und Certbot bleibt im Guide beschrieben.

Details siehe **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)**.
