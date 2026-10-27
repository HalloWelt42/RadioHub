"""Aufnahmen über die Ablage: ablegen beim Aufnehmen, abspielen mit Range, Wellenform, Schnitt, Löschen,
Verschieben, Nachholen nach einem Neustart."""

from __future__ import annotations

import itertools
import json
import uuid
from datetime import datetime, timedelta

from backend.ablage import orte
from backend.config import get_arbeit_dir
from backend.database import db_session
from backend.services.aufnahmen import aufnahmen
from backend.services.audio_utils import probe_duration
from backend.services.recorder import RecordingSession, rec_manager
from conftest import ton


_SEKUNDEN = itertools.count()


def _sitzung(sender: str = "Testfunk", folder_id: int | None = None, ordner: str | None = None) -> dict:
    """Aufnahme-Eintrag wie nach dem Start; jede beginnt eine Sekunde später (eigener Ordner)."""
    sid = f"rec_test_{uuid.uuid4().hex[:8]}"
    beginn = datetime(2026, 10, 28, 14, 0, 0) + timedelta(seconds=next(_SEKUNDEN))
    pfad = orte.aufnahmeordner(sender, beginn, ordner)
    with db_session() as conn:
        conn.execute("""INSERT INTO sessions (id, station_uuid, station_name, stream_url, start_time, file_path,
                        status, codec, file_format, folder_id) VALUES (?, '', ?, '', ?, ?, 'completed', 'mp3', '.mp3', ?)""",
                     (sid, sender, beginn.isoformat(), pfad, folder_id))
    return aufnahmen.sitzung(sid)


async def _mit_stuecken(tmp_path, anzahl: int = 2, sekunden: float = 4.0) -> dict:
    sitzung = _sitzung()
    start = 0
    for i in range(anzahl):
        datei = ton(tmp_path / f"seg_{i}.mp3", sekunden, 300 + 100 * i)
        dauer = int(await probe_duration(datei) * 1000)
        await aufnahmen.teil_ablegen(sitzung["id"], i, f"Titel {i + 1}", start, dauer, datei)
        start += dauer
    return sitzung


async def test_teil_ablegen_legt_in_die_ablage_und_raeumt_lokal(speicher, tmp_path):
    sitzung = _sitzung()
    datei = ton(tmp_path / "seg_000.mp3")
    await aufnahmen.teil_ablegen(sitzung["id"], 0, "Erster Titel", 0, 6000, datei)
    seg = aufnahmen.segmente(sitzung["id"])[0]
    assert seg["file_path"] == f"{sitzung['file_path']}/001 Erster Titel.mp3"
    assert seg["file_path"] in speicher.dateien and seg["file_size"] > 0
    assert not datei.exists()


async def test_wiedergabe_mit_range(client, speicher, tmp_path):
    sitzung = await _mit_stuecken(tmp_path, 1)
    seg = aufnahmen.segmente(sitzung["id"])[0]
    inhalt = speicher.dateien[seg["file_path"]]
    ganz = client.get(f"/api/recording/segments/{seg['id']}/play")
    assert ganz.status_code == 200 and ganz.content == inhalt
    assert ganz.headers["accept-ranges"] == "bytes"
    teil = client.get(f"/api/recording/segments/{seg['id']}/play", headers={"Range": "bytes=100-199"})
    assert teil.status_code == 206 and teil.content == inhalt[100:200]
    assert teil.headers["content-range"] == f"bytes 100-199/{len(inhalt)}"
    ende = client.get("/api/recordings/play", params={"path": seg["file_path"]}, headers={"Range": "bytes=-10"})
    assert ende.status_code == 206 and ende.content == inhalt[-10:]
    assert client.get("/api/recordings/play", params={"path": "Aufnahmen/gibt/es/nicht.mp3"}).status_code == 404


async def test_wellenform_entsteht_in_der_ablage(client, speicher, tmp_path):
    sitzung = await _mit_stuecken(tmp_path, 2)
    info = client.get(f"/api/recording/sessions/{sitzung['id']}/peaks/info").json()
    assert info["has_cache"] is False
    antwort = client.get(f"/api/recording/sessions/{sitzung['id']}/peaks", params={"start": 1, "duration": 2})
    assert antwort.status_code == 200
    assert int(antwort.headers["x-chunk-samples"]) == 200 and len(antwort.content) == 800
    assert orte.wellenform(sitzung["file_path"]) in speicher.dateien
    assert client.get(f"/api/recording/sessions/{sitzung['id']}/peaks/info").json()["has_cache"] is True
    audio = client.get(f"/api/recording/sessions/{sitzung['id']}/audio")
    assert audio.status_code == 200 and len(audio.content) > 0


async def test_schnitt_schreibt_neue_stuecke_und_raeumt_alte_in_den_papierkorb(client, speicher, tmp_path):
    sitzung = await _mit_stuecken(tmp_path, 2)
    alte = {s["file_path"] for s in aufnahmen.segmente(sitzung["id"])}
    antwort = client.post(f"/api/recording/sessions/{sitzung['id']}/custom-split",
                          json={"cut_points": [2.0, 5.0], "trim_start": True})
    assert antwort.status_code == 200, antwort.text
    assert antwort.json()["segments"] == 2 and antwort.json()["trimmed"] == 1
    neue = aufnahmen.segmente(sitzung["id"])
    assert [s["segment_index"] for s in neue] == [0, 1]
    assert all(s["file_path"] in speicher.dateien for s in neue)
    assert all(p in speicher.papierkorb for p in alte - {s["file_path"] for s in neue})
    assert not any(get_arbeit_dir("schnitt").glob(f"{sitzung['id']}*"))


async def test_segment_und_sitzung_loeschen_gehen_in_den_papierkorb(client, speicher, tmp_path):
    sitzung = await _mit_stuecken(tmp_path, 2)
    erstes, zweites = aufnahmen.segmente(sitzung["id"])
    assert client.delete(f"/api/recording/sessions/{sitzung['id']}/segments/{erstes['id']}").status_code == 200
    assert erstes["file_path"] in speicher.papierkorb
    assert [s["segment_index"] for s in aufnahmen.segmente(sitzung["id"])] == [0]
    assert client.delete(f"/api/recording/sessions/{sitzung['id']}").status_code == 200
    assert zweites["file_path"] in speicher.papierkorb
    assert aufnahmen.sitzung(sitzung["id"]) is None


async def test_verschieben_in_eigenen_ordner_und_umbenennen(client, speicher, tmp_path):
    sitzung = await _mit_stuecken(tmp_path, 1)
    ordner = client.post("/api/recording/folders", json={"name": "Konzerte"}).json()
    assert client.put(f"/api/recording/folders/move-session/{sitzung['id']}",
                      json={"folder_id": ordner["id"]}).json()["moved"] is True
    zeit = sitzung["file_path"].rsplit("/", 1)[-1]
    seg = aufnahmen.segmente(sitzung["id"])[0]
    assert seg["file_path"].startswith(f"Aufnahmen/Konzerte/Testfunk/{zeit}/")
    assert seg["file_path"] in speicher.dateien
    assert client.put(f"/api/recording/folders/{ordner['id']}", json={"name": "Live"}).status_code == 200
    seg = aufnahmen.segmente(sitzung["id"])[0]
    assert seg["file_path"].startswith("Aufnahmen/Live/Testfunk/") and seg["file_path"] in speicher.dateien
    assert aufnahmen.sitzung(sitzung["id"])["file_path"] == f"Aufnahmen/Live/Testfunk/{zeit}"
    antwort = client.delete(f"/api/recording/folders/{ordner['id']}")
    assert antwort.status_code == 400  # noch eine Aufnahme darin


async def test_explorer_listet_und_loescht_ueber_die_ablage(client, speicher, tmp_path):
    sitzung = await _mit_stuecken(tmp_path, 2)
    daten = client.get("/api/files/recordings").json()
    ordner = next(f for f in daten["folders"] if f["dir_name"] == "Testfunk")
    assert ordner["orphaned"] is False and ordner["file_count"] >= 2
    pfad = aufnahmen.segmente(sitzung["id"])[0]["file_path"]
    assert client.delete("/api/files/delete", params={"path": pfad}).status_code == 200
    assert pfad in speicher.papierkorb and len(aufnahmen.segmente(sitzung["id"])) == 1
    assert client.delete("/api/files/delete", params={"path": "../geheim"}).status_code == 403
    zip_antwort = client.post("/api/files/download-zip", json={"files": [aufnahmen.segmente(sitzung["id"])[0]["file_path"]]})
    assert zip_antwort.status_code == 200 and zip_antwort.content[:2] == b"PK"


async def test_aufnahme_abschliessen_legt_rest_und_titelliste_ab(speicher, tmp_path):
    sitzung = _sitzung("Abschlussfunk")
    session = RecordingSession(sitzung["id"], "", "Abschlussfunk", "")
    session.session_dir = get_arbeit_dir("aufnahmen", sitzung["id"])
    session.meta_file_path = session.session_dir / orte.TITELLISTE
    session.meta_file_path.write_text(json.dumps({"entries": [{"t": 0, "title": "Lied"}]}))
    session.current_segment_file = ton(session.session_dir / "seg_000.mp3")
    session.current_segment_title = "Lied"
    session.events.append({"type": "gap_start", "t": 1000, "detail": "Test"})
    await rec_manager._abschliessen(session, "completed")
    segmente = aufnahmen.segmente(sitzung["id"])
    assert [s["title"] for s in segmente] == ["Lied"]
    sitzung = aufnahmen.sitzung(sitzung["id"])
    assert sitzung["status"] == "completed" and sitzung["file_size"] > 0
    assert sitzung["meta_file_path"] == orte.titelliste(sitzung["file_path"])
    assert json.loads(speicher.dateien[sitzung["meta_file_path"]])["events"][0]["type"] == "gap_start"
    assert not session.session_dir.exists()


async def test_liegengebliebene_aufnahme_wird_nachgeholt(speicher, tmp_path):
    sitzung = _sitzung("Neustartfunk")
    arbeit = get_arbeit_dir("aufnahmen", sitzung["id"])
    ton(arbeit / "seg_000.mp3")
    ton(arbeit / "seg_001.mp3")
    assert await aufnahmen.liegengebliebene_ablegen() >= 2
    assert len(aufnahmen.segmente(sitzung["id"])) == 2
    assert not arbeit.exists()


async def test_ohne_ablage_kommt_eine_klare_meldung(client, tmp_path):
    from backend.ablage import KeineAblage, vorgeben
    vorgeben(KeineAblage("Kellerwolke nicht eingerichtet"))
    antwort = client.get("/api/files/recordings")
    assert antwort.status_code == 503 and "nicht eingerichtet" in antwort.json()["detail"]


async def test_umwandeln_schreibt_neue_datei_und_normalisieren_neue_version(client, speicher, tmp_path):
    sitzung = await _mit_stuecken(tmp_path, 1)
    alt = aufnahmen.segmente(sitzung["id"])[0]["file_path"]
    strom = client.post(f"/api/recording/sessions/{sitzung['id']}/convert", json={"format": "aac", "bitrate": 64})
    assert '"type": "done"' in strom.text, strom.text
    neu = aufnahmen.segmente(sitzung["id"])[0]["file_path"]
    assert neu == alt[:-4] + ".m4a" and neu in speicher.dateien and alt in speicher.papierkorb
    strom = client.post(f"/api/recording/sessions/{sitzung['id']}/normalize", json={"target_lufs": -18})
    assert '"type": "done"' in strom.text, strom.text
    assert speicher.versionen[neu] == 2
