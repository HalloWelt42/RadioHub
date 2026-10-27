"""Was umzieht: Dateien mit Ziel in der Ablage und die Übernahme in die Datenbank, für beide Quellen.

Zuordnung altes Radio (pyradio.db) -> RadioHub:
- favorites -> favorites (gleiche Spalten); doppelt, wenn uuid, url oder url_resolved schon da sind
- podcast_subscriptions -> podcast_subscriptions; doppelt, wenn die Feed-Adresse (ohne http/https, ohne Schrägstrich
  am Ende, klein) schon da ist; übernommen: feed_url, title, author, description, image_url, last_updated,
  created_at, auto_download, last_auto_download
- podcast_episodes -> podcast_episodes (je Abo über guid, vorhandene bleiben unverändert); übernommen: guid, title,
  description, audio_url, duration, published_at, resume_position
- podcast_saved_episodes (gemerkte Folgen mit Datei) -> Folge heruntergeladen (is_downloaded, local_path = Pfad in der
  Ablage, file_size) und podcast_saved_episodes; ist die Folge im RadioHub schon heruntergeladen, bleibt es dabei
- recordings/radio und recordings/edits -> je Datei eine Aufnahme "Altes Radio" mit einem Stück (sessions, segments)
- nicht übernommen: stations (Senderliste kommt aus dem Verzeichnis), sessions, schedules, export_jobs (leer),
  alarms, config, config.json, backups/
"""

from __future__ import annotations

import re
import shutil
import sqlite3
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from ..ablage import orte
from ..config import AUDIO_EXTENSIONS

ALTES_RADIO = "Altes Radio"
OHNE_ZUORDNUNG = f"{orte.AUFNAHMEN}/Ohne Zuordnung"


@dataclass
class Datei:
    """Eine Datei, die in die Ablage zieht; `eintragen` schreibt danach die Datenbank (Ziel, Größe)."""

    teil: str
    quelle: Path
    ziel: str
    eintragen: Optional[Callable[[sqlite3.Connection, str, int], None]] = None


@dataclass
class Bericht:
    zeilen: dict[str, int] = field(default_factory=dict)
    hinweise: list[str] = field(default_factory=list)

    def zaehlen(self, was: str, anzahl: int = 1) -> None:
        self.zeilen[was] = self.zeilen.get(was, 0) + anzahl


def feed_schluessel(url: str | None) -> str:
    return re.sub(r"^https?://", "", (url or "").strip().lower()).rstrip("/")


def lokal(pfad: str, wurzel: Path) -> Path:
    """Pfad einer Quelldatei: wie gespeichert, sonst unter `wurzel/recordings` (Pfade aus einem anderen Container)."""
    p = Path(pfad)
    if p.exists() or "/recordings/" not in pfad:
        return p
    return wurzel / "recordings" / pfad.split("/recordings/", 1)[1]


def _dauer_s(datei: Path) -> float:
    try:
        aus = subprocess.run(["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0",
                              str(datei)], capture_output=True, text=True, timeout=30).stdout.strip()
        return float(aus or 0)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return 0.0


def eindeutig(dateien: list[Datei]) -> list[Datei]:
    """Jede Quelle einmal, jedes Ziel einmal (gleiche Ziele bekommen einen Zähler, stabile Reihenfolge)."""
    gesehen_quellen: set[Path] = set()
    vergeben: set[str] = set()
    ergebnis = []
    for d in sorted(dateien, key=lambda d: (d.ziel, str(d.quelle))):
        if d.quelle in gesehen_quellen:
            continue
        gesehen_quellen.add(d.quelle)
        ziel, zaehler = d.ziel, 2
        stamm, punkt, endung = d.ziel.rpartition(".")
        while ziel in vergeben:
            ziel = f"{stamm} ({zaehler}).{endung}" if punkt else f"{d.ziel} ({zaehler})"
            zaehler += 1
        vergeben.add(ziel)
        d.ziel = ziel
        ergebnis.append(d)
    return ergebnis


# --- Heutiges RadioHub ------------------------------------------------------------------------------------------------

def _ordner_name(conn: sqlite3.Connection, folder_id) -> str | None:
    if folder_id is None:
        return None
    row = conn.execute("SELECT name FROM recording_folders WHERE id = ?", (folder_id,)).fetchone()
    return row["name"] if row else None


def radiohub_datenbank(conn: sqlite3.Connection, daten: Path, schreiben: bool, bericht: Bericht) -> None:
    """Aufnahmen bekommen ihren Ordner in der Ablage; fehlende Titellisten werden ausgetragen."""
    rows = conn.execute("SELECT * FROM sessions WHERE file_path LIKE '/%' OR meta_file_path LIKE '/%'").fetchall()
    for s in rows:
        ordner = orte.aufnahmeordner(s["station_name"], s["start_time"], _ordner_name(conn, s["folder_id"]))
        meta = s["meta_file_path"]
        meta_fehlt = bool(meta) and meta.startswith("/") and not lokal(meta, daten).exists()
        bericht.zaehlen("RadioHub: Aufnahmen mit neuem Ordner")
        if schreiben:
            conn.execute("UPDATE sessions SET file_path = ? WHERE id = ?", (ordner, s["id"]))
            if meta_fehlt:
                conn.execute("UPDATE sessions SET meta_file_path = NULL WHERE id = ?", (s["id"],))
    if schreiben:
        conn.commit()


def radiohub_dateien(conn: sqlite3.Connection, daten: Path, bericht: Bericht) -> list[Datei]:
    dateien: list[Datei] = []
    belegt: set[Path] = set()
    abos = {r["id"]: r["title"] for r in conn.execute("SELECT id, title FROM podcast_subscriptions")}

    for e in conn.execute("""SELECT id, podcast_id, local_path, title, published_at FROM podcast_episodes
                             WHERE local_path LIKE '/%'""").fetchall():
        quelle = lokal(e["local_path"], daten)
        belegt.add(quelle)
        if not quelle.is_file():
            bericht.zaehlen("RadioHub: Folge eingetragen, Datei fehlt")
            continue

        def eintragen(c, ziel, groesse, eid=e["id"]):
            c.execute("UPDATE podcast_episodes SET local_path = ?, file_size = ?, is_downloaded = 1 WHERE id = ?",
                      (ziel, groesse, eid))
        abo = abos.get(e["podcast_id"]) or f"Unbekannter Podcast {e['podcast_id']}"
        dateien.append(Datei("RadioHub: Podcast-Folgen", quelle,
                             orte.folge(abo, e["title"] or quelle.stem, e["published_at"], quelle.suffix), eintragen))

    for seg in conn.execute("""SELECT seg.id, seg.segment_index, seg.title, seg.file_path, s.station_name,
                                      s.start_time, s.folder_id
                               FROM segments seg JOIN sessions s ON s.id = seg.session_id
                               WHERE seg.file_path LIKE '/%'""").fetchall():
        quelle = lokal(seg["file_path"], daten)
        belegt.add(quelle)
        if not quelle.is_file():
            bericht.zaehlen("RadioHub: Stück eingetragen, Datei fehlt")
            continue
        ordner = orte.aufnahmeordner(seg["station_name"], seg["start_time"], _ordner_name(conn, seg["folder_id"]))

        def eintragen(c, ziel, groesse, sid=seg["id"]):
            c.execute("UPDATE segments SET file_path = ?, file_size = ? WHERE id = ?", (ziel, groesse, sid))
        dateien.append(Datei("RadioHub: Aufnahmen", quelle,
                             orte.stueck(ordner, seg["segment_index"], seg["title"] or "Teil", quelle.suffix),
                             eintragen))

    for s in conn.execute("SELECT * FROM sessions WHERE meta_file_path LIKE '/%'").fetchall():
        quelle = lokal(s["meta_file_path"], daten)
        belegt.add(quelle)
        if not quelle.is_file():
            continue
        ordner = orte.aufnahmeordner(s["station_name"], s["start_time"], _ordner_name(conn, s["folder_id"]))

        def eintragen(c, ziel, groesse, sid=s["id"]):
            c.execute("UPDATE sessions SET meta_file_path = ? WHERE id = ?", (ziel, sid))
        dateien.append(Datei("RadioHub: Titellisten", quelle, orte.titelliste(ordner), eintragen))

    # Ton ohne Eintrag in der Datenbank zieht trotzdem um ("jede Datei")
    audio = daten / "recordings" / "podcasts" / "audio"
    for quelle in sorted((daten / "recordings").rglob("*")) if (daten / "recordings").exists() else []:
        if not quelle.is_file() or quelle in belegt or quelle.suffix.lower() not in AUDIO_EXTENSIONS:
            continue
        if quelle.is_relative_to(audio):
            pid = quelle.relative_to(audio).parts[0]
            abo = abos.get(int(pid)) if pid.isdigit() else None
            ziel = f"{orte.podcastordner(abo or f'Unbekannter Podcast {pid}')}/{orte.name(quelle.name)}"
        else:
            ziel = f"{OHNE_ZUORDNUNG}/{orte.name(quelle.name)}"
        dateien.append(Datei("RadioHub: Ton ohne Eintrag", quelle, ziel))
    return dateien


def radiohub_bilder(daten: Path, cache: Path, schreiben: bool, bericht: Bericht) -> None:
    """Cover sind Zwischenspeicher: sie ziehen in den Cache (cache/podcast-bilder), nicht in die Ablage."""
    bilder = daten / "recordings" / "podcasts" / "images"
    if not bilder.exists():
        return
    for quelle in sorted(p for p in bilder.rglob("*") if p.is_file()):
        ziel = cache / "podcast-bilder" / quelle.relative_to(bilder)
        if ziel.exists():
            continue
        bericht.zaehlen("RadioHub: Cover in den Cache")
        if schreiben:
            ziel.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(quelle, ziel)


# --- Altes Radio ------------------------------------------------------------------------------------------------------

def altes_radio_datenbank(conn: sqlite3.Connection, alt: sqlite3.Connection, schreiben: bool, bericht: Bericht) -> None:
    """Favoriten, Abos und Folgen übernehmen, ohne Doppel; mehrfach ausführbar."""
    urls = set()
    for r in conn.execute("SELECT uuid, url, url_resolved FROM favorites"):
        urls |= {r["uuid"], r["url"], r["url_resolved"]} - {None, ""}
    for f in alt.execute("SELECT * FROM favorites ORDER BY added_at"):
        if {f["uuid"], f["url"], f["url_resolved"]} & urls:
            bericht.zaehlen("Altes Radio: Favoriten schon da")
            continue
        bericht.zaehlen("Altes Radio: Favoriten neu")
        urls |= {f["uuid"], f["url"], f["url_resolved"]} - {None, ""}
        if schreiben:
            conn.execute("""INSERT INTO favorites (uuid, name, url, url_resolved, favicon, country, countrycode, tags,
                            bitrate, added_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                         (f["uuid"], f["name"], f["url"], f["url_resolved"], f["favicon"], f["country"],
                          f["countrycode"], f["tags"], f["bitrate"], f["added_at"]))

    abos = {feed_schluessel(r["feed_url"]): r["id"] for r in conn.execute("SELECT id, feed_url FROM podcast_subscriptions")}
    for s in alt.execute("SELECT * FROM podcast_subscriptions ORDER BY id"):
        schluessel = feed_schluessel(s["feed_url"])
        if schluessel in abos:
            bericht.zaehlen("Altes Radio: Abos schon da")
            neu_id = abos[schluessel]
        else:
            bericht.zaehlen("Altes Radio: Abos neu")
            neu_id = None
            if schreiben:
                neu_id = conn.execute("""INSERT INTO podcast_subscriptions (feed_url, title, author, description,
                                         image_url, last_updated, created_at, auto_download, last_auto_download)
                                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                      (s["feed_url"], s["title"], s["author"], s["description"], s["image_url"],
                                       s["last_updated"], s["created_at"], s["auto_download"],
                                       s["last_auto_download"])).lastrowid
                abos[schluessel] = neu_id
        folgen = alt.execute("""SELECT guid, title, description, audio_url, duration, published_at, resume_position
                                FROM podcast_episodes WHERE podcast_id = ?""", (s["id"],)).fetchall()
        for e in folgen:
            vorhanden = neu_id is not None and conn.execute(
                "SELECT 1 FROM podcast_episodes WHERE podcast_id = ? AND guid = ?", (neu_id, e["guid"])).fetchone()
            if vorhanden:
                bericht.zaehlen("Altes Radio: Folgen schon da")
                continue
            bericht.zaehlen("Altes Radio: Folgen neu")
            if schreiben:
                conn.execute("""INSERT OR IGNORE INTO podcast_episodes (podcast_id, guid, title, description, audio_url,
                                duration, published_at, resume_position) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                             (neu_id, e["guid"], e["title"], e["description"], e["audio_url"], e["duration"],
                              e["published_at"], e["resume_position"]))
    if schreiben:
        conn.commit()


def _folge_im_radiohub(conn: sqlite3.Connection, feed_url: str, guid: str):
    for abo in conn.execute("SELECT id, feed_url FROM podcast_subscriptions"):
        if feed_schluessel(abo["feed_url"]) == feed_schluessel(feed_url):
            return conn.execute("SELECT * FROM podcast_episodes WHERE podcast_id = ? AND guid = ?",
                                (abo["id"], guid)).fetchone()
    return None


def _start_aus_name(datei: Path) -> datetime:
    treffer = re.search(r"(\d{8})_(\d{6})", datei.name)
    if treffer:
        return datetime.strptime("".join(treffer.groups()), "%Y%m%d%H%M%S")
    return datetime.fromtimestamp(datei.stat().st_mtime)


def altes_radio_dateien(conn: sqlite3.Connection, alt: sqlite3.Connection, wurzel: Path,
                        bericht: Bericht) -> list[Datei]:
    dateien: list[Datei] = []
    belegt: set[Path] = set()

    for se in alt.execute("""SELECT se.file_path, e.guid, e.title, e.published_at, s.feed_url, s.title AS abo
                             FROM podcast_saved_episodes se
                             JOIN podcast_episodes e ON e.id = se.episode_id
                             JOIN podcast_subscriptions s ON s.id = se.podcast_id""").fetchall():
        quelle = lokal(se["file_path"] or "", wurzel)
        belegt.add(quelle)
        if not quelle.is_file():
            bericht.zaehlen("Altes Radio: gemerkte Folge, Datei fehlt")
            continue
        im_radiohub = _folge_im_radiohub(conn, se["feed_url"], se["guid"])
        if im_radiohub is not None and im_radiohub["is_downloaded"] and im_radiohub["local_path"]:
            bericht.zaehlen("Altes Radio: gemerkte Folge im RadioHub schon heruntergeladen")
            continue

        def eintragen(c, ziel, groesse, feed=se["feed_url"], guid=se["guid"]):
            folge = _folge_im_radiohub(c, feed, guid)
            if folge is None:
                return
            c.execute("UPDATE podcast_episodes SET is_downloaded = 1, local_path = ?, file_size = ? WHERE id = ?",
                      (ziel, groesse, folge["id"]))
            if not c.execute("SELECT 1 FROM podcast_saved_episodes WHERE episode_id = ?", (folge["id"],)).fetchone():
                c.execute("""INSERT INTO podcast_saved_episodes (podcast_id, episode_id, file_path, size_mb)
                             VALUES (?, ?, ?, ?)""", (folge["podcast_id"], folge["id"], ziel,
                                                      round(groesse / 1024 / 1024, 2)))
        dateien.append(Datei("Altes Radio: gemerkte Folgen", quelle,
                             orte.folge(se["abo"] or "Unbekannter Podcast", se["title"] or quelle.stem,
                                        se["published_at"], quelle.suffix), eintragen))

    podcasts = wurzel / "recordings" / "podcasts"
    for quelle in sorted(podcasts.rglob("*")) if podcasts.exists() else []:
        if quelle.is_file() and quelle not in belegt and quelle.suffix.lower() in AUDIO_EXTENSIONS:
            ordner = quelle.relative_to(podcasts).parts[0] if len(quelle.relative_to(podcasts).parts) > 1 else ""
            dateien.append(Datei("Altes Radio: Podcast-Ton ohne Eintrag", quelle,
                                 f"{orte.podcastordner(ordner or 'Unbekannter Podcast')}/{orte.name(quelle.name)}"))

    for unterordner, titel in (("radio", "Aufnahme"), ("edits", "Schnitt")):
        quellen = wurzel / "recordings" / unterordner
        for quelle in sorted(quellen.rglob("*")) if quellen.exists() else []:
            if not quelle.is_file() or quelle.suffix.lower() not in AUDIO_EXTENSIONS:
                continue
            beginn = _start_aus_name(quelle)
            ordner = orte.aufnahmeordner(ALTES_RADIO, beginn, None)
            dauer = _dauer_s(quelle)
            sid = f"alt_{quelle.stem}"

            def eintragen(c, ziel, groesse, sid=sid, ordner=ordner, beginn=beginn, dauer=dauer, titel=titel,
                          endung=quelle.suffix.lower()):
                c.execute("""INSERT OR IGNORE INTO sessions (id, station_uuid, station_name, stream_url, start_time,
                             end_time, duration, file_path, file_size, status, file_format, rec_type)
                             VALUES (?, '', ?, '', ?, ?, ?, ?, ?, 'completed', ?, 'uebernahme')""",
                          (sid, ALTES_RADIO, beginn.isoformat(), beginn.isoformat(), dauer, ordner, groesse, endung))
                if not c.execute("SELECT 1 FROM segments WHERE session_id = ?", (sid,)).fetchone():
                    c.execute("""INSERT INTO segments (session_id, segment_index, title, start_ms, end_ms, duration_ms,
                                 file_path, file_size) VALUES (?, 0, ?, 0, ?, ?, ?, ?)""",
                              (sid, titel, int(dauer * 1000), int(dauer * 1000), ziel, groesse))
            dateien.append(Datei("Altes Radio: Aufnahmen", quelle, orte.stueck(ordner, 0, titel, quelle.suffix),
                                 eintragen))
    return dateien
