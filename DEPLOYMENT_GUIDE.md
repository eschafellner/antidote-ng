# Antidote – Der ultimative Deployment- & Betriebsguide

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
   - [Schritt 2: Tunnel mit 1 Klick starten](#schritt-2-tunnel-mit-1-klick-starten)
   - [Schritt 3: Fachlichen Ablauf live testen](#schritt-3-fachlichen-ablauf-live-testen)
   - [Bonus: Feste eigene Domain mit Cloudflare Tunnel](#bonus-feste-eigene-domain-mit-cloudflare-tunnel)
4. [Weg 3: Eigener Linux-VPS mit echter Domain & HTTPS](#4-weg-3-eigener-linux-vps-mit-echter-domain--https)
   - [Voraussetzungen](#voraussetzungen)
   - [Schritt 1: Server vorbereiten (One-Shot Setup)](#schritt-1-server-vorbereiten-one-shot-setup)
   - [Schritt 2: Repository klonen](#schritt-2-repository-klonen)
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
- Startet den Django-Server im Produktionsmodus.

---

## 3. Weg 2: Sofort online via Cloudflare Tunnel (Ohne Serverkauf)

### Warum Cloudflare Tunnel?
Mit einem Cloudflare Tunnel kannst du deine lokale Antidote-Instanz innerhalb von 30 Sekunden weltweit über das Internet erreichbar machen.
- **Keine Portweiterleitung (Port Forwarding)** am WLAN-Router nötig.
- **Keine Freigabe der eigenen IP-Adresse** (sicher vor Port-Scans).
- **Automatisches, echtes HTTPS-Zertifikat** von Cloudflare.
- Voll funktionsfähig: Login, CSRF-Schutz, Kanban-Drag&Drop und Dateiuploads funktionieren 1:1 wie auf einem Server.

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

#### 🪟 Windows (PowerShell als Administrator):
```powershell
winget install --id Cloudflare.cloudflared
```

---

### Schritt 2: Tunnel mit 1 Klick starten

Führe im Projektverzeichnis einfach folgendes Skript aus:
```bash
./deploy/start_tunnel.sh
```

**Was passiert automatisch?**
1. Das Skript prüft, ob die Frontend-Assets gebaut wurden (falls nicht, baut es sie mit `npm run build`).
2. Es sammelt statische Dateien (`collectstatic`).
3. Es startet Django auf `127.0.0.1:8000`.
4. Es startet den Cloudflare Quick Tunnel.

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

1. **Login:** Mit `admin` / `admin123` anmelden.
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

### Bonus: Feste eigene Domain mit Cloudflare Tunnel
Wenn du eine eigene Domain bei Cloudflare verwaltest (z. B. `antidote.meine-firma.de`), kannst du einen dauerhaften, festen Namen nutzen:

1. Einmalig anmelden:
   ```bash
   cloudflared tunnel login
   ```
2. Tunnel anlegen:
   ```bash
   cloudflared tunnel create antidote
   ```
3. DNS-Eintrag verknüpfen:
   ```bash
   cloudflared tunnel route dns antidote antidote.meine-firma.de
   ```
4. Tunnel dauerhaft starten:
   ```bash
   cloudflared tunnel run --url http://127.0.0.1:8000 antidote
   ```

---

## 4. Weg 3: Eigener Linux-VPS mit echter Domain & HTTPS

Für den dauerhaften Betrieb im Produktivmodus empfehlen wir einen günstigen Linux-VPS (z. B. Hetzner Cloud CX22 ab ~4 €/Monat oder GCP e2-micro / Ubuntu 24.04 oder 26.04).

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
3. Lade das Setup-Skript herunter (oder kopiere den Projektordner) und führe es aus:
   ```bash
   sudo bash deploy/setup_server.sh antidote.meine-domain.de
   ```
   *(Ersetze `antidote.meine-domain.de` durch deine tatsächliche Domain).*

**Was richtet das Skript automatisch ein?**
- Richtet 2 GB Swap-Speicher ein (verhindert Speicherüberläufe beim Frontend-Build auf kleinen Servern).
- Installiert Nginx, Python 3, Node.js 22 LTS, Certbot und Fail2ban.
- Erstellt den System-User `antidote` und die Ordnerstruktur unter `/var/www/antidote/`.
- Richtet den systemd-Dienst `/etc/systemd/system/antidote.service` ein.
- Konfiguriert Nginx mit Gzip-Kompression, Caching und X-Accel-Redirect für geschützte Anhänge.
- Schärft die Firewall (`ufw`) für SSH und Web-Traffic.

---

### Schritt 2: Repository klonen

Als Benutzer `antidote` das Repository in das Verzeichnis `/var/www/antidote/app` klonen:
```bash
sudo -u antidote git clone https://github.com/DEIN_USER/antidote-ng.git /var/www/antidote/app
```

---

### Schritt 3: `.env` Datei anlegen

Erstelle die Konfigurationsdatei für den Server:
```bash
sudo nano /var/www/antidote/app/.env
```

Füge folgenden Inhalt ein (Passe Domain und Secret Key an):
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

Führe das Zero-Downtime-Deployment-Skript aus:
```bash
sudo bash /var/www/antidote/app/deploy.sh
```

**Was macht `deploy.sh`?**
1. Erstellt das Python Virtual Environment (`/var/www/antidote/venv`) und installiert alle Bibliotheken.
2. Baut die Vue 3-Assets mit Vite (`npm ci && npm run build`).
3. Kopiert statische Dateien mit `manage.py collectstatic`.
4. Führt Datenbankmigrationen aus und schaltet SQLite in den extrem performanten WAL-Modus (`PRAGMA journal_mode=WAL`).
5. Lädt den Gunicorn-Server über systemd ohne Downtime neu.

#### Initialen Admin-Benutzer anlegen:
```bash
sudo -u antidote /var/www/antidote/venv/bin/python /var/www/antidote/app/manage.py createsuperuser
```
*(Oder führe `python manage.py seed_demo_data` aus, falls du Beispieldaten wünschst).*

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
Das Skript zieht die neuesten Commits (`git pull`), baut geänderte Assets neu, führt eventuelle neue Datenbankmigrationen aus und startet die Gunicorn-Worker sanft neu.

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
