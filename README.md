# RadioHub - Digital Audio System

Webbasiertes Internetradio, Podcast-Player und Audiorecorder mit HiFi-Optik.
Konzipiert für Raspberry Pi, läuft aber auf jedem System mit Python und Node.js.

![RadioHub Dark & Light Mode](media/hero-dark-light.png)

---

## Features

### Tuner - Internetradio

Zugriff auf tausende Sender weltweit über die Radio-Browser-API.
Filterbar nach Land, Bitrate, Codec und Votes. Favoritenverwaltung inklusive.

![Tuner - Senderübersicht](media/feature-tuner.png)

- Sendersuche mit Echtzeit-Filter und Sortierung
- Länderliste mit Senderanzahl
- Favoritensystem mit Drag-and-Drop-Sortierung
- Sender-Details: Homepage, Codec, Bitrate, Stream-URL
- Favicon-Caching für schnelle Darstellung
- Laufschrift mit aktuellem Titel (ICY-Metadata)

### Recorder - Aufnahmen

Laufende Streams mitschneiden, segmentieren und bearbeiten.
Integrierter Waveform-Cutter für präzises Schneiden.

![Recorder - Aufnahmen](media/feature-recorder.png)

- Zeitgesteuerte und manuelle Aufnahme
- Waveform-basierter Audio-Cutter mit Minimap
- Segment-Schnitt per Doppelklick oder Tastatur
- Normalisierung (LUFS) und Format-Konvertierung (MP3, FLAC, OGG, WAV)
- Datei-Explorer mit Sortierung und Segment-Selektion

### Podcasts

RSS-Feeds abonnieren, Episoden streamen oder herunterladen.

![Podcasts](media/feature-podcasts.png)

- Podcast-Suche und Abonnement-Verwaltung
- Episoden-Filter: Alle, Ungehört, Downloads
- Streaming und Offline-Downloads
- Automatische Feed-Aktualisierung

### Setup

Umfangreiche Einstellungen für Darstellung, Sprache und System.

![Setup - Einstellungen](media/feature-settings.png)

- Dark Mode und Light Mode
- 20+ Sprachen mit Flaggen-Auswahl
- Aufnahme-Einstellungen (Format, Qualität, Speicherpfad)
- Timeshift-Buffer-Konfiguration
- System-Informationen und Dienste-Verwaltung

### HiFi-Player

Der Player orientiert sich an klassischer HiFi-Geräte-Optik:

- Gebürstetes Edelstahl-Design (Brushed Metal)
- VU-Meter mit Echtzeit-Pegelanzeige
- Transport-Buttons im Hardware-Look
- Drehregler für Lautstärke
- LED-Anzeigen für Status und Navigation
- Laufschrift-Display mit Stream-Titel
- Tastatursteuerung (Space, Pfeiltasten, 1-4 für Tabs)

### Light Mode

Alle Oberflächen sind auch im hellen Design verfügbar.

![Tuner - Light Mode](media/feature-tuner-light.png)

---

## Technik

| Komponente | Technologie |
|------------|-------------|
| Frontend | Svelte 5 (Runes), Vite, hls.js |
| Backend | Python, FastAPI, FFmpeg |
| Audio | HLS-Streaming, ICY-Metadata, LUFS-Normalisierung |
| Datenbank | SQLite |
| Icons | Font Awesome 6 |
| Fonts | Orbitron (Logo), Barlow (UI) |

### Architektur

```
radiohub-frontend/    Svelte 5 SPA (Port 5180)
radiohub-backend/     FastAPI REST-API (Port 9091)
  backend/
    routers/          API-Endpunkte
    services/         Business-Logik, Audio-Verarbeitung
    database.py       SQLite-Anbindung
```

### Installation per Docker (empfohlen, Pi und Mac)

Voraussetzung: Docker mit Compose-Plugin.

```bash
git clone git@github.com:HalloWelt42/RadioHub.git
cd RadioHub
docker compose up -d
```

Aufruf:

- App: `http://localhost:9092` (bzw. `http://<host-ip>:9092` im LAN)
- Backend-API direkt: `http://localhost:9091`
- API-Docs: `http://localhost:9092/docs`

Daten (Datenbank, Aufnahmen, Cache) liegen in `./data` neben dem Repo.

Updates:

```bash
git pull
docker compose up -d --build
```

### Lokale Entwicklung (ohne Docker)

Voraussetzungen: Python 3.11+, Node.js 18+, FFmpeg.

```bash
# Backend
cd radiohub-backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Frontend
cd ../radiohub-frontend
npm install
```

Starten:

```bash
# Backend (Port 9091)
cd radiohub-backend
source .venv/bin/activate
uvicorn backend.main:app --host 0.0.0.0 --port 9091 --reload

# Frontend Dev-Server (Port 5180, mit Vite-Proxy auf 9091)
cd radiohub-frontend
npm run dev
```

Die App ist im Dev-Modus unter `http://localhost:5180` erreichbar.

---

## Lizenz

Nicht-kommerzielle Lizenz v1.0 (`LicenseRef-RadioHub-NC-1.0`)
Basierend auf [CC BY-NC-ND 4.0](https://creativecommons.org/licenses/by-nc-nd/4.0/legalcode.de) mit Ergänzungen.

Copyright 2025-2026 HalloWelt42

Private, nicht-kommerzielle Nutzung und private Modifikation erlaubt.
Kommerzielle Nutzung, Verkauf und Veröffentlichung modifizierter Versionen untersagt.
Vollständige Lizenzbedingungen: [lizenz.md](radiohub-frontend/public/legal/de/lizenz.md)
