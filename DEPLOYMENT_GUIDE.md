# Antidote – Deployment und Betrieb

Dieses Dokument erklärt Schritt für Schritt, wie **Antidote** betrieben und bereitgestellt werden kann. Es richtet sich sowohl an Entwickler als auch an Einsteiger mit wenig IT-Erfahrung.

---

## Inhaltsverzeichnis

1. [Übersicht der drei Wege](#1-übersicht-der-drei-wege)
2. [Weg 1: Lokaler Testserver (Auf deinem Rechner)](#2-weg-1-lokaler-testserver-auf-deinem-rechner)
   - [A. Entwicklungsmodus (Hot Module Reloading)](#a-entwicklungsmodus-hot-module-reloading)
   - [B. Lokaler Produktions-Preview (Wie auf dem Live-Server)](#b-lokaler-produktions-preview-wie-auf-dem-live-server)
3. [Weg 2: Sofort online via Cloudflare Tunnel (Ohne Serverkauf)](#3-weg-2-sofort-online-via-cloudflare-tunnel-ohne-serverkauf)
   - [Warum Cloudflare Tunnel?](#warum-cloudflare-tunnel)
   - [Schritt 1: `cloudflared` installieren](#schritt-1-cloudflared-installieren)
   - [Schritt 2: Tunnel starten](#schritt-2-tunnel-starten)
   - [Schritt 3: Fachlichen Ablauf live testen](#schritt-3-fachlichen-ablauf-live-testen)
4. [Weg 3: Eigener Linux-VPS mit echter Domain & HTTPS](#4-weg-3-eigener-linux-vps-mit-echter-domain--https)
   - [Empfohlen: Docker Compose](#empfohlen-docker-compose)
   - [Docker Compose mit Cloudflare Tunnel](#docker-compose-mit-cloudflare-tunnel)
   - [Alternative: Manuelles Setup ohne Docker](#alternative-manuelles-setup-ohne-docker)
   - [Schritt 1: Server vorbereiten (One-Shot Setup)](#schritt-1-server-vorbereiten-one-shot-setup)
   - [Schritt 2: Repository und Setup prüfen](#schritt-2-repository-und-setup-prüfen)
   - [Schritt 3: `.env` Datei anlegen](#schritt-3-env-datei-anlegen)
   - [Schritt 4: Deployment ausführen](#schritt-4-deployment-ausführen)
   - [Schritt 5: Kostenloses SSL-Zertifikat (HTTPS) aktivieren](#schritt-5-kostenloses-ssl-zertifikat-https-aktivieren)
   - [Laufender Betrieb & Updates](#laufender-betrieb--updates)
5. [Fehlerbehebung & FAQ](#5-fehlerbehebung--faq)

---

## 1. Übersicht der drei Wege

| Weg | Wann nutzen? | Kosten | Eigene Domain? | Echte HTTPS-URL? |
|---|---|---|---|---|
| **1. Lokaler Server** | Beim Entwickeln, UI anpassen oder schnellen Offline-Testen | 0 € | Nein (`localhost`) | Nein (HTTP) |
| **2. Cloudflare Tunnel** | Wenn du Kollegen, Kunden oder Testern sofort einen Link schicken willst – ohne Server mieten zu müssen | 0 € | Optional (auch Zufalls-URL) | **Ja** (echtes HTTPS) |
| **3. Eigener Linux-VPS** | Für den dauerhaften, professionellen Produktiveinsatz im Team oder Unternehmen | Ab ~4 €/Monat | **Ja** (z. B. `antidote.de`) | **Ja** (Let's Encrypt) |

---

## 2. Weg 1: Lokaler Testserver (Auf deinem Rechner)

### Voraussetzungen
- **Python 3.12+** (getestet bis Python 3.14)
- **Node.js 20+** und **npm**
- **Git**

### A. Entwicklungsmodus (Hot Module Reloading)
Im Entwicklungsmodus werden Code-Änderungen an Vue-Komponenten oder CSS sofort ohne Neuladen im Browser sichtbar.

1. **Terminal im Projektordner öffnen.**
2. **Lokalen Schnellstarter ausführen:**
   ```bash
   ./run_local.sh --dev --seed
   ```
   *Was macht dieser Befehl?*
   - Erstellt automatisch eine virtuelle Python-Umgebung (`.venv`), falls nicht vorhanden.
   - Installiert alle Python- und Node-Pakete.
   - Führt Datenbank-Migrationen aus und lädt Demodaten (`--seed`).
   - Startet das Django-Backend auf Port `8000` und den Vite-Dev-Server auf Port `5173`.

3. **Im Browser öffnen:**  
   👉 [http://127.0.0.1:8000](http://127.0.0.1:8000)
   - **Login:** `admin`
   - **Passwort:** `admin123`

---

### B. Lokaler Produktions-Preview (Wie auf dem Live-Server)
Wenn du vor dem Online-Stellen prüfen willst, wie sich die fertig gebündelten Skripte und Assets verhalten:

```bash
./run_local.sh --preview
```
*Was macht dieser Befehl?*
- Kompiliert das Vue 3-Frontend mit Vite zu produktionsoptimierten JS/CSS-Bundles (`npm run build`).
- Sammelt alle Dateien über `collectstatic`.
- Startet den Django-Entwicklungsserver mit gebauten Assets. Dies ist eine lokale Vorschau, kein Produktionsserver.

---

## 3. Weg 2: Sofort online via Cloudflare Tunnel (Ohne Serverkauf)

### Warum Cloudflare Tunnel?
Ein Cloudflare Quick Tunnel macht deine lokale Antidote-Instanz öffentlich erreichbar. Verwende dafür nur Testdaten und Konten mit eigenen, starken Passwörtern.
- **Keine Portweiterleitung (Port Forwarding)** am WLAN-Router nötig.
- **Keine Freigabe der eigenen IP-Adresse** (sicher vor Port-Scans).
- **Automatisches, echtes HTTPS-Zertifikat** von Cloudflare.
- Der Starter setzt `DEBUG=False`, sichere Cookies und die Tunnel-Domain als erlaubten Host. Ein Neustart erzeugt einen neuen Sitzungsschlüssel; bestehende Sitzungen müssen sich neu anmelden.

---

### Schritt 1: `cloudflared` installieren

Wähle dein Betriebssystem (nur 1x nötig):

#### 🐧 Linux (Ubuntu / Debian):
```bash
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared.deb && rm cloudflared.deb
```

#### 🍏 macOS:
```bash
brew install cloudflared
```

#### 🪟 Windows:
Die Startskripte sind Bash-Skripte. Nutze WSL mit Ubuntu und installiere Python, Node.js und `cloudflared` **innerhalb von WSL** nach der Linux-Anleitung. Eine reine PowerShell-Installation reicht für `./deploy/start_tunnel.sh` nicht aus.

---

### Schritt 2: Tunnel starten

Richte zuerst Python-Abhängigkeiten, Frontend und Datenbank lokal ein:
```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
npm ci
.venv/bin/python manage.py migrate
```
Falls noch kein Admin-Konto existiert, lege eines mit `.venv/bin/python manage.py createsuperuser` an. Falls du zuvor `--seed` verwendet hast, ändere **alle** Demo-Passwörter (`admin`, `developer`, `viewer`) mit `.venv/bin/python manage.py changepassword BENUTZERNAME`. Der Tunnel-Starter bricht ab, solange eines dieser bekannten Passwörter aktiv ist.

Starte danach im Projektverzeichnis:
```bash
./deploy/start_tunnel.sh
```

**Was passiert automatisch?**
1. Das Skript baut fehlende Frontend-Assets, führt Migrationen aus und sammelt statische Dateien.
2. Es verweigert den Start bei bekannten Demo-Passwörtern oder belegtem lokalen Port.
3. Es startet Django auf `127.0.0.1:8000` und danach den Cloudflare Quick Tunnel.

Nach wenigen Sekunden siehst du im Terminal eine Ausgabe wie diese:
```text
+--------------------------------------------------------------------------------------------+
|  Your quick Tunnel has been created! Visit it at (it may take some time to be reachable):  |
|  https://alpha-bravo-delta-echo.trycloudflare.com                                          |
+--------------------------------------------------------------------------------------------+
```

---

### Schritt 3: Fachlichen Ablauf live testen

Kopiere die angezeigte `https://...trycloudflare.com` URL und öffne sie in deinem Browser (oder teile sie mit Kollegen):

1. **Login:** Mit dem selbst angelegten Konto oder einem Demo-Konto mit geändertem Passwort anmelden.
2. **Projekt & Issues testen:**
   - Neues Issue anlegen (Titel, Typ, Priorität, Assignee).
   - Issue im Kanban-Board per Drag & Drop zwischen den Spalten verschieben (z. B. *To Do* → *In Progress* → *Done*).
   - In die Detailansicht wechseln (Slide-Over-Drawer öffnet sich).
   - Einen Markdown-Kommentar verfassen und formatieren.
   - Einen Dateianhang (z. B. PNG, PDF oder TXT) hochladen und wieder herunterladen.
3. **Einladung & Rollen testen:**
   - In die Projekteinstellungen wechseln (`Settings`).
   - Einen Einladungslink generieren und in einem privaten/Inkognito-Fenster öffnen.
   - Als neuer Benutzer registrieren und überprüfen, ob der automatische Beitritt klappt.

> [!TIP]
> **Beenden des Tunnels:**  
> Drücke im Terminal einfach `Strg + C`. Django und der Tunnel werden sauber gestoppt.

---

## 4. Weg 3: Eigener Linux-VPS mit echter Domain & HTTPS

Für den dauerhaften Betrieb auf einem Linux-VPS gibt es zwei Wege. **Docker Compose ist der einfachere Weg für eine neue Installation.** Das bisherige manuelle Setup bleibt als Alternative erhalten.

### Empfohlen: Docker Compose

Dieser Weg startet zwei Container: Django mit Gunicorn und Caddy als HTTPS-Reverse-Proxy. Das Frontend wird beim Image-Build gebaut; Migrationen und `collectstatic` laufen beim Start des App-Containers. SQLite-Daten, Uploads, statische Dateien und Caddy-Zertifikate liegen auf benannten Docker-Volumes und überstehen Container-Neustarts. Geschützte Anhänge werden nach dem Django-Berechtigungscheck durch die App ausgeliefert.

**Voraussetzungen:** Ein VPS mit öffentlicher Domain, deren DNS-A-Record auf den Server zeigt; Ports 80 und 443 müssen erreichbar und frei sein. Installiere [Docker Engine samt Compose-Plugin nach der offiziellen Ubuntu-Anleitung](https://docs.docker.com/engine/install/ubuntu/). Auf diesem Weg werden Nginx, Certbot, Node.js und Python **nicht** auf dem VPS installiert. Caddy beschafft und erneuert das HTTPS-Zertifikat automatisch.

1. Verbinde dich mit dem VPS und klone das Repository:
   ```bash
   ssh root@DEINE_SERVER_IP
   apt update && apt install -y git
   git clone https://github.com/eschafellner/antidote-ng.git /opt/antidote-ng
   cd /opt/antidote-ng
   ```
   Ersetze die Repository-URL, falls du einen eigenen Fork verwendest.
2. Lege die Docker-Konfiguration an:
   ```bash
   cp deploy/docker.env.example deploy/docker.env
   python3 -c 'import secrets; print(secrets.token_urlsafe(64))'
   nano deploy/docker.env
   chmod 600 deploy/docker.env
   ```
   Setze `DOMAIN` auf deinen echten Hostnamen und ersetze `SECRET_KEY` durch die erzeugte Zeichenfolge. Verwende keine Beispielwerte. `deploy/docker.env` wird nicht eingecheckt.
3. Prüfe die Konfiguration und starte die Container:
   ```bash
   docker compose --env-file deploy/docker.env config --quiet
   docker compose --env-file deploy/docker.env up -d --build
   docker compose --env-file deploy/docker.env ps
   ```
   Warte, bis `app` als `healthy` angezeigt wird. Caddy startet danach. Öffne `https://DEINE_DOMAIN` erst, wenn DNS und HTTPS bereit sind.
4. Lege den ersten Admin an:
   ```bash
   docker compose --env-file deploy/docker.env exec app python manage.py createsuperuser
   ```
   Verwende auf diesem Server **nicht** `seed_demo_data`; der Befehl erzeugt Konten mit bekannten Passwörtern.

**Updates** werden im Repository-Verzeichnis ausgeführt:
```bash
git pull --ff-only
docker compose --env-file deploy/docker.env up -d --build
docker compose --env-file deploy/docker.env ps
```
Für Logs: `docker compose --env-file deploy/docker.env logs -f app caddy`. Der App-Container führt beim Neustart Migrationen aus; bei nicht kompatiblen Datenbankänderungen ist eine Wartungszeit möglich. Sichere regelmäßig das `data`-Volume (SQLite) und das `media`-Volume (Uploads). Verwende bei laufender SQLite-Datenbank die SQLite-Backup-API statt einer einfachen Dateikopie. `docker compose down --volumes` löscht die Datenvolumes und ist kein Update-Befehl.

**Bestehende Installation:** Dieser Weg übernimmt weder die Datenbank noch Uploads aus `/var/www/antidote/` automatisch. Stoppe einen vorhandenen Nginx-Dienst vor dem Docker-Start, da er sonst die Ports 80/443 belegt. Plane eine gesonderte Datenmigration mit Backup, bevor du umstellst.

### Docker Compose mit Cloudflare Tunnel

Wenn deine Domain über Cloudflare verwaltet wird, kannst du Antidote stattdessen über einen **verwalteten Cloudflare Tunnel** bereitstellen. Dabei laufen `app` und `cloudflared` als zwei Container im selben Compose-Netzwerk. Die App hat keine öffentlich freigegebenen Ports; für diesen Weg brauchst du weder Caddy noch offene Ports 80/443 oder einen DNS-A-Record auf die Server-IP. Die Verbindung vom Browser zu Cloudflare nutzt HTTPS. Die statischen Dateien liefert WhiteNoise aus dem App-Container aus.

1. Richte `deploy/docker.env` wie oben beschrieben ein. `DOMAIN` muss genau dem späteren öffentlichen Hostnamen entsprechen, beispielsweise `antidote.example.com`. Lege in der [Cloudflare-Oberfläche einen verwalteten Tunnel](https://developers.cloudflare.com/tunnel/get-started/) an und kopiere dessen **Token** (nur die Zeichenfolge, nicht den angezeigten Docker-Befehl) in eine zusätzliche Zeile der Datei:
   ```text
   TUNNEL_TOKEN=DEIN_TUNNEL_TOKEN
   ```
   Halte diese Datei privat (`chmod 600 deploy/docker.env`). Wer den Token besitzt, kann den Tunnel starten.
2. Erstelle im Cloudflare-Tunnel eine Route vom öffentlichen Hostnamen `DOMAIN` zur **Service URL `http://app:8000`**. `app` ist der Compose-Dienstname. `localhost` würde aus Sicht des `cloudflared`-Containers auf diesen Container selbst zeigen.
3. Starte nur die beiden benötigten Dienste:
   ```bash
   docker compose -f compose.yaml -f compose.tunnel.yaml --env-file deploy/docker.env config --quiet
   docker compose -f compose.yaml -f compose.tunnel.yaml --env-file deploy/docker.env up -d --build app cloudflared
   docker compose -f compose.yaml -f compose.tunnel.yaml --env-file deploy/docker.env ps
   ```
   Falls zuvor Caddy mit derselben Compose-Installation gestartet wurde, stoppe ihn mit `docker compose --env-file deploy/docker.env stop caddy`. Danach ist Antidote unter `https://DEINE_DOMAIN` erreichbar. Prüfe bei Problemen die Logs mit `docker compose -f compose.yaml -f compose.tunnel.yaml --env-file deploy/docker.env logs -f app cloudflared`.
4. Lege den ersten Admin an:
   ```bash
   docker compose -f compose.yaml -f compose.tunnel.yaml --env-file deploy/docker.env exec app python manage.py createsuperuser
   ```

Für Updates nutze `git pull --ff-only` und danach erneut den `up -d --build app cloudflared`-Befehl aus Schritt 3. Die benannten Volumes für Datenbank und Uploads bleiben erhalten. Sichere sie wie im Abschnitt oben beschrieben. Ein Cloudflare Quick Tunnel mit zufälliger Adresse ist für diesen festen `DOMAIN`-Weg nicht vorgesehen; dafür gibt es weiterhin [Weg 2](#3-weg-2-sofort-online-via-cloudflare-tunnel-ohne-serverkauf).

### Alternative: Manuelles Setup ohne Docker

Das folgende Setup verwendet Nginx, Gunicorn, systemd und Certbot direkt auf dem VPS.

### Architektur auf dem Server
- **Nginx:** Hört auf Port 80 & 443 (HTTPS), liefert CSS/JS/Bilder blitzschnell direkt aus und leitet App-Anfragen per Unix-Socket an Gunicorn weiter.
- **Gunicorn (WSGI):** Läuft isoliert unter dem System-Benutzer `antidote` und wird vom `systemd`-Dienst überwacht (automatischer Neustart bei Absturz oder Server-Reboot).
- **SQLite im WAL-Modus (oder PostgreSQL):** Gespeichert in `/var/www/antidote/data/` (außerhalb des Git-Ordners, dadurch geschützt vor versehentlichem Überschreiben bei Updates).
- **Let's Encrypt (Certbot):** Kostenloses SSL-Zertifikat mit automatischer Verlängerung.

---

### Schritt 1: Server vorbereiten (One-Shot Setup)

1. Verbinde dich per SSH mit deinem neuen Server:
   ```bash
   ssh root@DEINE_SERVER_IP
   ```
2. Setze im DNS-Verwaltungsmenü deiner Domain einen **A-Record** für deine Domain (z. B. `antidote.meine-domain.de`) auf die IP-Adresse deines Servers.
3. Installiere Git, klone das Repository und starte dann das Setup aus dem geklonten Verzeichnis:
   ```bash
   sudo apt update
   sudo apt install -y git
   sudo mkdir -p /var/www/antidote
   sudo git clone https://github.com/eschafellner/antidote-ng.git /var/www/antidote/app
   sudo bash /var/www/antidote/app/deploy/setup_server.sh antidote.meine-domain.de
   ```
   Ersetze die Domain und gegebenenfalls die Repository-URL. Das Setup übergibt den geklonten Ordner an den Systembenutzer `antidote`. Bis zum ersten Deployment liefert Nginx für App-Anfragen noch keinen gültigen Inhalt.

**Was richtet das Skript automatisch ein?**
- Richtet 2 GB Swap-Speicher ein (verhindert Speicherüberläufe beim Frontend-Build auf kleinen Servern).
- Installiert Nginx, Python 3, Node.js 22 LTS, Certbot und Fail2ban.
- Erstellt den System-User `antidote` und die Ordnerstruktur unter `/var/www/antidote/`.
- Richtet den systemd-Dienst `/etc/systemd/system/antidote.service` ein.
- Konfiguriert Nginx mit Gzip-Kompression, Caching und X-Accel-Redirect für geschützte Anhänge.
- Schärft die Firewall (`ufw`) für SSH und Web-Traffic.

---

### Schritt 2: Repository und Setup prüfen

Prüfe, ob das Repository jetzt dem Dienstbenutzer gehört und der Nginx-Dienst läuft:
```bash
sudo -u antidote git -C /var/www/antidote/app status --short
sudo systemctl status nginx
```

---

### Schritt 3: `.env` Datei anlegen

Erzeuge zuerst einen zufälligen Schlüssel und notiere ihn für die Konfiguration:
```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(64))'
```

Erstelle dann die Konfigurationsdatei für den Server:
```bash
sudo nano /var/www/antidote/app/.env
```

Füge folgenden Inhalt ein (ersetze Domain und `SECRET_KEY` durch den erzeugten Schlüssel):
```ini
DEBUG=False
SECRET_KEY=generiere-hier-einen-langen-zufaelligen-schluessel-12345
ALLOWED_HOSTS=antidote.meine-domain.de,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://antidote.meine-domain.de

# Datenbank (gespeichert im persistenten Datenverzeichnis)
DATABASE_URL=sqlite:////var/www/antidote/data/db.sqlite3

# Statische Dateien & Uploads (performant via Nginx)
STATIC_ROOT=/var/www/antidote/staticfiles
MEDIA_ROOT=/var/www/antidote/media
USE_X_ACCEL_REDIRECT=True

# Maximale Uploadgröße (15 MB)
MAX_ATTACHMENT_SIZE_BYTES=15728640
```
> Speichern mit `Strg + O`, Enter, dann Beenden mit `Strg + X`.

Sichere die Datei ab:
```bash
sudo chown antidote:www-data /var/www/antidote/app/.env
sudo chmod 640 /var/www/antidote/app/.env
```

---

### Schritt 4: Deployment ausführen

Führe das Deployment-Skript aus:
```bash
sudo bash /var/www/antidote/app/deploy.sh
```

**Was macht `deploy.sh`?**
1. Erstellt das Python Virtual Environment (`/var/www/antidote/venv`) und installiert alle Bibliotheken.
2. Baut die Vue 3-Assets mit Vite (`npm ci && npm run build`).
3. Kopiert statische Dateien mit `manage.py collectstatic`.
4. Führt Datenbankmigrationen aus und aktiviert für SQLite den WAL-Modus.
5. Startet den Gunicorn-Dienst oder lädt ihn bei Updates neu. Bei nicht kompatiblen Migrationen kann eine Wartungszeit nötig sein.

#### Initialen Admin-Benutzer anlegen:
```bash
sudo -u antidote /var/www/antidote/venv/bin/python /var/www/antidote/app/manage.py createsuperuser
```
`seed_demo_data` erzeugt Konten mit bekannten Passwörtern und ist nur für lokale Testumgebungen geeignet.

---

### Schritt 5: Kostenloses SSL-Zertifikat (HTTPS) aktivieren

Dank Certbot genügt ein einziger Befehl:
```bash
sudo certbot --nginx -d antidote.meine-domain.de
```
- Gib deine E-Mail-Adresse für wichtige Verlängerungs-Benachrichtigungen ein.
- Wähle die automatische Weiterleitung von HTTP auf HTTPS.
- Fertig! Das Zertifikat verlängert sich künftig vollautomatisch.

Jetzt ist deine Antidote-Instanz unter **`https://antidote.meine-domain.de`** live und produktionsbereit! 🚀

---

### Laufender Betrieb & Updates

Wenn du neuen Code auf GitHub gepusht hast und deinen Live-Server aktualisieren willst:
```bash
ssh root@DEINE_SERVER_IP
sudo bash /var/www/antidote/app/deploy.sh
```
Das Skript zieht den konfigurierten Upstream-Branch als Benutzer `antidote` mit `git pull --ff-only`. Bei einem Git-Fehler stoppt es, statt einen erfolgreichen Update-Lauf vorzutäuschen. Anschließend baut es Assets, führt Migrationen aus und lädt Gunicorn neu. Plane bei Datenbankänderungen gegebenenfalls ein Wartungsfenster ein.

---

## 5. Fehlerbehebung & FAQ

### Problem 1: "403 Forbidden – CSRF verification failed"
- **Ursache:** Die Domain wurde nicht in `CSRF_TRUSTED_ORIGINS` eingetragen oder das Protokoll (`https://`) fehlt.
- **Lösung:** In der `.env`-Datei prüfen:
  ```ini
  CSRF_TRUSTED_ORIGINS=https://antidote.meine-domain.de
  ```
  *(Bei Cloudflare Quick Tunnel: `https://*.trycloudflare.com`)*.  
  Anschließend Gunicorn neu laden: `sudo systemctl reload antidote`.

### Problem 2: "DisallowedHost (400) / Invalid HTTP_HOST header"
- **Ursache:** Die Domain fehlt in `ALLOWED_HOSTS`.
- **Lösung:** In `.env` eintragen:
  ```ini
  ALLOWED_HOSTS=antidote.meine-domain.de,localhost,127.0.0.1
  ```

### Problem 3: Seitenlayout zerschossen / CSS und JS laden nicht
- **Ursache:** Das Frontend-Bundle wurde nicht gebaut oder statische Dateien nicht gesammelt.
- **Lösung:**
  ```bash
  npm run build
  python manage.py collectstatic --noinput
  ```

### Problem 4: Serverstatus & Logs überprüfen
- Status des Gunicorn-Dienstes ansehen:
  ```bash
  sudo systemctl status antidote
  ```
- Live-Logs der Anwendung mitverfolgen:
  ```bash
  sudo journalctl -u antidote -f
  ```
- Nginx-Fehlerlogs prüfen:
  ```bash
  sudo tail -f /var/log/nginx/error.log
  ```
- Anwendungs-Error-Logs prüfen:
  ```bash
  sudo tail -f /var/log/antidote/error.log
  ```
