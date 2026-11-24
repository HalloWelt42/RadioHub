"""Feinschnitt einer laufenden Aufnahme in Abschnitten (RAD-139): dasselbe Ergebnis wie auf einmal, begrenzter Platz, Rückgängig."""

import asyncio
import shutil
import subprocess
from datetime import datetime

import pytest
from test_stromleser import mp3  # noqa: F401 - Fixture

from app.ablage import AblageFehler, ablage
from app.config import get_arbeit_dir
from app.database import db_session
from app.services import feinschnitt_lauf, laufschnitt as lauf_modul, recorder as recorder_modul
from app.sendewerbung.sitzung import Werbestelle
from app.services.aufnahmen import TITEL_ZAEHLT, aufnahmen
from app.services.empfang import Abschnitt
from app.services.laufschnitt import Laufschnitt
from app.services.schnitt import gegenstand, schritte

LIED_S, LIEDER, ANGABE_S = 30.0, 12, 1.5
GANZ_S = LIED_S * LIEDER
#: Wechsel an den Nähten; das vierte "Lied" ist Werbung
WECHSEL = [(0.0, "Lied 0", False)] + [(i * LIED_S + ANGABE_S, f"Lied {i}", False) for i in range(1, LIEDER) if i != 4]
STILLEN = [(i * LIED_S - 0.6, i * LIED_S) for i in range(1, LIEDER)]
SPOT = Werbestelle(von=4 * LIED_S, bis=5 * LIED_S, von_aus="angabe", format="creative", kennung="spot")
ERWARTET = ["Lied 0", "Lied 1", "Lied 2", "Lied 3", "Werbung: spot", *[f"Lied {i}" for i in range(5, LIEDER)]]


def empfang(von: float, dauer: float) -> Abschnitt:
    bis = von + dauer
    return Abschnitt(dauer, [], [(max(0.0, v - von), min(dauer, b - von)) for v, b in STILLEN if b > von and v < bis], [],
                     [(max(0.0, SPOT.von - von), min(dauer, SPOT.bis - von), SPOT)] if SPOT.bis > von and SPOT.von < bis else [])


@pytest.fixture(scope="module")
def grobe(tmp_path_factory):
    """Grob geteilte Stücke, wie der Rekorder sie beim Eintreffen der Angaben ablegt."""
    ordner = tmp_path_factory.mktemp("grob")
    grenzen = [t for t, _, _ in WECHSEL] + [GANZ_S]
    aus = []
    for i, (von, bis) in enumerate(zip(grenzen, grenzen[1:])):
        ziel = ordner / f"seg_{i:03d}.mp3"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"sine=frequency={300 + 40 * i}:sample_rate=22050:duration={bis - von}",
                        "-b:a", "32k", str(ziel)], check=True)
        aus.append((WECHSEL[i][1], int(von * 1000), int((bis - von) * 1000), ziel))
    return aus


@pytest.fixture
def sitzung(client):
    kennung = f"rec_lauf_{datetime.now().timestamp()}"
    with db_session() as conn:
        conn.execute("""INSERT INTO sessions (id, station_uuid, station_name, stream_url, start_time, status, file_path)
                        VALUES (?, 's', 'Probe Radio', 'http://x', '2026-11-24T10:00:00', 'recording', ?)""", (kennung, f"Aufnahmen/{kennung}"))
    yield kennung
    shutil.rmtree(get_arbeit_dir("schnitt") / f"{kennung}_lauf", ignore_errors=True)


async def _aufnehmen(kennung, grobe, tmp_path, nach_jedem):
    """Ein Stück nach dem anderen ablegen; `wechsel` kennt nur, was schon gesendet wurde."""
    bis = [0.0]
    lauf = Laufschnitt(kennung, empfang, lambda: [w for w in WECHSEL if w[0] <= bis[0]], asyncio.Lock())
    for nr, (titel, start, dauer, datei) in enumerate(grobe):
        kopie = tmp_path / datei.name
        shutil.copyfile(datei, kopie)
        bis[0] = (start + dauer) / 1000
        lokal = lauf.platz_fuer(nr, ".mp3")
        fertig = await aufnahmen.teil_ablegen(kennung, nr, titel, start, dauer, kopie, lokal)
        if lokal:
            lauf.gehalten(fertig["path"], lokal)
        await nach_jedem(lauf)
    return lauf


def _lueckenlos(kennung, ganz_ms=int(GANZ_S * 1000)):
    zeilen = aufnahmen.segmente(kennung)
    assert [z["segment_index"] for z in zeilen] == list(range(len(zeilen)))
    assert zeilen[0]["start_ms"] == 0 and zeilen[-1]["end_ms"] == ganz_ms
    assert all(abs(a["end_ms"] - b["start_ms"]) <= 60 for a, b in zip(zeilen, zeilen[1:])), zeilen
    return zeilen


async def test_in_abschnitten_wie_auf_einmal_und_ruecknehmbar(sitzung, grobe, tmp_path, monkeypatch):
    monkeypatch.setattr(lauf_modul, "ABSCHNITT_S", 70.0)
    monkeypatch.setattr(lauf_modul, "NACHLAUF_S", 20.0)
    lokal, staende = [], []

    async def nach_jedem(lauf):
        if lauf.faellig():
            await lauf.durchgang()
        ordner = get_arbeit_dir("schnitt") / f"{sitzung}_lauf"
        lokal.append(len(list(ordner.rglob("*.mp3"))) if ordner.exists() else 0)
        staende.append(len(_lueckenlos(sitzung, aufnahmen.segmente(sitzung)[-1]["end_ms"])))
        for z in aufnahmen.segmente(sitzung):                            # zu jeder Zeit hörbar: jede Zeile hat ihre Datei
            assert (await ablage().eintrag(z["file_path"])).groesse > 0

    lauf = await _aufnehmen(sitzung, grobe, tmp_path, nach_jedem)
    assert lauf._nr >= 3 and max(lokal) <= 6, (lauf._nr, lokal)          # lokal bleibt nur der laufende Abschnitt
    await lauf.durchgang(abschluss=True)
    zeilen = _lueckenlos(sitzung)
    assert [z["title"] for z in zeilen] == ERWARTET
    for i, z in enumerate(zeilen):                                       # Grenzen an den Pausen, nicht an den Angaben
        assert abs(z["start_ms"] / 1000 - i * LIED_S) < 0.4, (i, z)
    assert [(round(n.von), round(n.bis)) for n in lauf.werbung] == [(120, 150)]
    assert not (get_arbeit_dir("schnitt") / f"{sitzung}_lauf").exists()
    # auf einmal, aus der Analyse neu gerechnet, kommt dasselbe heraus
    analyse = await feinschnitt_lauf.analyse_lesen(sitzung)
    assert abs(analyse.dauer - GANZ_S) < 0.1
    plan = feinschnitt_lauf.planen(analyse, 3)
    assert [s.name for s in plan] == ERWARTET and all(abs(s.von - z["start_ms"] / 1000) < 0.2 for s, z in zip(plan, zeilen))
    # ein Schritt, und zurückgenommen liegt alles grob wie aufgenommen
    feinschnitt_lauf.status_setzen(sitzung, "completed")
    g = gegenstand("sitzung", sitzung)
    assert [s["was"] for s in schritte(g.schluessel)] == [f"Feinschnitt: {len(ERWARTET)} Stücke an den Pausen, Werbung für sich"]
    assert (await g.rueckgaengig()).startswith("Feinschnitt")
    wieder = aufnahmen.segmente(sitzung)
    assert [(z["title"], z["start_ms"], z["duration_ms"]) for z in wieder] == [(t, s, d) for t, s, d, _ in grobe]
    for z in wieder:
        assert await ablage().eintrag(z["file_path"])
    dateien = [e.name for e in await ablage().liste(f"Aufnahmen/{sitzung}") if e.name.endswith(".mp3")]
    assert len(dateien) == len(grobe), dateien                           # weder feine noch Reste bleiben liegen


async def test_ablage_weg_mitten_im_durchgang_verliert_nichts(sitzung, grobe, tmp_path, monkeypatch):
    monkeypatch.setattr(lauf_modul, "ABSCHNITT_S", 70.0)
    monkeypatch.setattr(lauf_modul, "NACHLAUF_S", 20.0)
    echt, noch = ablage().ablegen, [0]

    async def stockend(pfad, datei):
        if "_lauf" in str(datei) and noch[0] < 4:                        # der erste Durchgang scheitert nach einigen Stücken
            noch[0] += 1
            if noch[0] >= 2:
                raise AblageFehler("weg")
        return await echt(pfad, datei)

    monkeypatch.setattr(ablage(), "ablegen", stockend)
    gescheitert = []

    async def nach_jedem(lauf):
        if lauf.faellig():
            try:
                await lauf.durchgang()
            except AblageFehler:
                gescheitert.append(1)
        for z in aufnahmen.segmente(sitzung):
            assert (await ablage().eintrag(z["file_path"])).groesse > 0

    lauf = await _aufnehmen(sitzung, grobe, tmp_path, nach_jedem)
    await lauf.durchgang(abschluss=True)
    assert gescheitert
    assert [z["title"] for z in _lueckenlos(sitzung)] == ERWARTET


async def test_langer_titel_wird_in_teilen_fein(sitzung, grobe, tmp_path, monkeypatch):
    """Ein Sender ohne Titelwechsel: der Rekorder teilt stündlich, der Feinschnitt gibt fertige Teile frei, statt ewig zu sammeln."""
    monkeypatch.setattr(lauf_modul, "ABSCHNITT_S", 70.0)
    monkeypatch.setattr(lauf_modul, "NACHLAUF_S", 20.0)
    monkeypatch.setattr(lauf_modul, "LANG_S", 100.0)
    monkeypatch.setitem(globals(), "WECHSEL", [(0.0, "Sendung", False)])
    monkeypatch.setitem(globals(), "STILLEN", [])
    monkeypatch.setitem(globals(), "SPOT", Werbestelle(von=-2, bis=-1, von_aus="angabe", format="creative", kennung="x"))
    gehalten = []

    async def nach_jedem(lauf):
        if lauf.faellig():
            await lauf.durchgang()
        gehalten.append(len(aufnahmen.segmente(sitzung)) - lauf.fertig)

    lauf = await _aufnehmen(sitzung, [("Sendung", s, d, f) for _, s, d, f in grobe], tmp_path, nach_jedem)
    await lauf.durchgang(abschluss=True)
    namen = [z["title"] for z in _lueckenlos(sitzung)]
    assert max(gehalten) <= 6 and namen[:2] == ["Sendung", "Sendung (Teil 2)"], (gehalten, namen)


async def test_zweiter_stopp_wartet_auf_den_ersten(monkeypatch):
    rec = recorder_modul.RecorderManager()
    laeufe = []

    async def langsam():
        laeufe.append(1)
        await asyncio.sleep(0.1)
        return {"success": True}

    monkeypatch.setattr(rec, "_stoppen", langsam)
    assert await asyncio.gather(rec.stop(), rec.stop()) == [{"success": True}] * 2
    assert len(laeufe) == 1


async def test_reserve_der_datentraeger(client, monkeypatch):
    from app.ablage.port import Platz
    rec = recorder_modul.rec_manager
    assert await rec._platz_voll() == "" or "Server" in await rec._platz_voll()

    class Wenig:
        free = 3 * recorder_modul.GB
    monkeypatch.setattr(recorder_modul.shutil, "disk_usage", lambda _: Wenig)
    assert "3.0 GB frei (Reserve 5 GB)" in await rec._platz_voll()
    Wenig.free = 50 * recorder_modul.GB
    assert await rec._platz_voll() == ""

    async def knapp():
        return Platz(gesamt=100 * recorder_modul.GB, frei=recorder_modul.GB)
    monkeypatch.setattr(ablage(), "platz", knapp)
    assert "Kellerwolke" in await rec._platz_voll()
    assert not (await rec.start("s", "Probe", "http://127.0.0.1:9/x", 64))["success"]


def test_titelzahl_ohne_werbung_und_senderkennung(sitzung, client):
    stuecke = [("A - Eins", 200_000), ("Probe Radio", 6_000), ("Werbung: X", 30_000), ("Einschub", 4_000), ("Probe Radio - Nachrichten", 180_000),
               ("B - Zwei", 15_000)]
    with db_session() as conn:
        for i, (t, d) in enumerate(stuecke):
            conn.execute("""INSERT INTO segments (session_id, segment_index, title, start_ms, end_ms, duration_ms, file_path, file_size)
                            VALUES (?, ?, ?, 0, ?, ?, ?, 1)""", (sitzung, i, t, d, d, f"x/{i}"))
        assert conn.execute(f"SELECT COUNT(*) FROM sessions s JOIN segments seg ON seg.session_id = s.id WHERE s.id = ? AND {TITEL_ZAEHLT}",
                            (sitzung,)).fetchone()[0] == 3
    feinschnitt_lauf.status_setzen(sitzung, "feinschnitt")
    feinschnitt_lauf.FORTSCHRITT[sitzung] = (2, 5)
    try:
        s = client.get(f"/api/recording/sessions/{sitzung}").json()
        assert (s["segment_count"], s["titel_count"], s["arbeit"]) == (6, 3, {"fertig": 2, "gesamt": 5})
        liste = client.get("/api/recording/sessions").json()
        assert liste["titel_gesamt"] >= 3 and next(x for x in liste["sessions"] if x["id"] == sitzung)["titel_count"] == 3
        # solange geschnitten wird: hören ja, ändern nein
        assert client.post("/api/schnitt/rueckgaengig", json={"art": "sitzung", "kennung": sitzung}).status_code == 409
    finally:
        feinschnitt_lauf.FORTSCHRITT.pop(sitzung)
        feinschnitt_lauf.status_setzen(sitzung, "completed")
    assert client.get("/api/recording/folders").status_code == 200


async def test_aufnahme_schneidet_waehrend_sie_laeuft(client, mp3, monkeypatch):
    """Im ganzen Ablauf: fertige Abschnitte sind schon während der Aufnahme fein, nach dem Stopp fehlt nur der letzte."""
    from test_stromleser import DREI, Sender
    monkeypatch.setattr(recorder_modul, "MIN_SEGMENT_SECONDS", 0)
    monkeypatch.setattr(lauf_modul, "ABSCHNITT_S", 11.0)
    monkeypatch.setattr(lauf_modul, "NACHLAUF_S", 3.0)
    rec = recorder_modul.rec_manager
    async with Sender(mp3 * 6, DREI, takt_s=0.1) as sender:
        ergebnis = await rec.start("s1", "Probesender", sender.adresse(), 64)
        assert ergebnis["success"], ergebnis
        lauf = rec.active_session.laufschnitt
        for _ in range(250):
            if lauf.fertig:
                break
            await asyncio.sleep(0.1)
        assert lauf.fertig == 1 and rec.active_session, "der erste Titel ist fein, während aufgenommen wird"
        fein = aufnahmen.segmente(ergebnis["session_id"])[0]
        assert fein["title"] == "A - Eins" and abs(fein["end_ms"] / 1000 - 8.0) < 0.6
        zeile = client.get(f"/api/recording/sessions/{ergebnis['session_id']}").json()
        assert zeile["duration"] > 13 and zeile["file_size"] > 0, "Länge und Größe stimmen schon während der Aufnahme"
        for _ in range(200):
            if rec.active_session.ton_s >= 20.0:
                break
            await asyncio.sleep(0.05)
        await rec.stop()
        await rec.feinschnitt_abwarten()
    namen = [z["title"] for z in aufnahmen.segmente(ergebnis["session_id"])]
    assert namen == ["A - Eins", "B - Zwei", "C - Drei"], namen
    sitzung = aufnahmen.sitzung(ergebnis["session_id"])
    assert sitzung["status"] == "completed" and sitzung["file_size"] == sum(z["file_size"] for z in aufnahmen.segmente(sitzung["id"]))
