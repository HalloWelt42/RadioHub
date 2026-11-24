"""Weitere Titel an eine Aufnahme anhängen (RAD-145): Zeiten, Werbung, Titelliste und Analyse gelten weiter, zurückgenommen wird
wieder eine eigene Aufnahme daraus, ein Abbruch mittendrin verliert nichts."""

import asyncio
import json

import pytest
from test_aufnahmen import _mit_stuecken
from test_stromleser import DREI, Sender, mp3  # noqa: F401 - Fixture

from app.ablage import AblageFehler, ablage
from app.database import db_session
from app.services import anhaengen as modul, feinschnitt_lauf, recorder as recorder_modul, werbestellen
from app.services.anhaengen import anhaengen, nachholen, ziel_pruefen
from app.services.aufnahmen import AufnahmeFehler, aufnahmen
from app.services.schnitt import gegenstand, schritte


def _setzen(sid, **werte):
    with db_session() as conn:
        conn.execute(f"UPDATE sessions SET {', '.join(f'{k} = ?' for k in werte)} WHERE id = ?", (*werte.values(), sid))


async def _paar(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    ziel, quelle = await _mit_stuecken(tmp_path / "a", 2), await _mit_stuecken(tmp_path / "b", 3)
    for s, titel in ((ziel, ["A", "B"]), (quelle, ["C", "D", "E"])):
        pfad = f"{s['file_path']}/Titelliste.json"
        await ablage().schreiben(pfad, json.dumps({"total_audio_bytes": 1000, "entries": [{"t": i * 4000, "b": i * 100, "title": t} for i, t in enumerate(titel)]}).encode())
        _setzen(s["id"], meta_file_path=pfad, station_uuid="u1")
        await feinschnitt_lauf.analyse_ablegen(s["id"], feinschnitt_lauf.Analyse(dauer=8, wechsel=[(0.0, titel[0], False), (4.0, titel[1], False)]))
    werbestellen.ersetzen(werbestellen.Bezug.aufnahme(quelle["id"]), "sendedaten", [werbestellen.Neu(von=1, bis=3.5, text="Spot")])
    _setzen(quelle["id"], ziel_id=ziel["id"])
    return ziel["id"], quelle["id"]


def _bild(sid):
    return [(z["segment_index"], z["title"], z["start_ms"], z["end_ms"], z["file_path"]) for z in aufnahmen.segmente(sid)]


async def _dateien_da(sid):
    for z in aufnahmen.segmente(sid):
        assert (await ablage().eintrag(z["file_path"])).groesse > 0, z


async def test_anhaengen_und_zuruecknehmen(client, tmp_path):
    ziel, quelle = await _paar(tmp_path)
    vorher, neu_vorher = _bild(ziel), _bild(quelle)
    ab = vorher[-1][3]
    assert await anhaengen(quelle) == 3
    zeilen = aufnahmen.segmente(ziel)
    assert [z["segment_index"] for z in zeilen] == [0, 1, 2, 3, 4] and _bild(ziel)[:2] == vorher
    assert [z["start_ms"] for z in zeilen[2:]] == [ab + x[2] for x in neu_vorher]
    assert all(z["file_path"].startswith(aufnahmen.sitzung(ziel)["file_path"] + "/0") for z in zeilen)
    await _dateien_da(ziel)
    s = client.get(f"/api/recording/sessions/{ziel}").json()
    assert abs(s["duration"] - sum(z["duration_ms"] for z in zeilen) / 1000) < 0.01 and s["file_size"] == sum(z["file_size"] for z in zeilen)
    # in keiner Liste, kein Zählen, aber vorhanden
    assert quelle not in [x["id"] for x in client.get("/api/recording/sessions?limit=500").json()["sessions"]]
    assert aufnahmen.sitzung(quelle)["status"] == "angehaengt"
    (w,) = werbestellen.stellen(werbestellen.Bezug.aufnahme(ziel))
    assert (w.von, w.bis) == (1 + ab / 1000, 3.5 + ab / 1000)
    liste = await aufnahmen.titelliste(aufnahmen.sitzung(ziel))
    assert [(e["title"], e["t"], e["b"]) for e in liste["entries"]][2:] == [("C", ab, 1000), ("D", ab + 4000, 1100), ("E", ab + 8000, 1200)]
    a = await feinschnitt_lauf.analyse_lesen(ziel)
    assert [x[1] for x in a.wechsel] == ["A", "B", "C", "D"] and a.wechsel[2][0] == round(ab / 1000, 3)
    g = gegenstand("sitzung", ziel)
    assert [x["was"] for x in schritte(g.schluessel)][-1].startswith("Angehängt: 3 Stücke vom 28.10.")
    assert (await g.info())["werbestellen"], "die Zeiten im Ton gelten weiter"
    # umgezogen in einen anderen Ordner lässt es sich weiter zurücknehmen
    await aufnahmen.sitzung_verschieben(ziel, "Sammlung", None)
    await _dateien_da(ziel)
    assert (await g.rueckgaengig()).startswith("Angehängt")
    assert [x[:4] for x in _bild(ziel)] == [x[:4] for x in vorher]
    assert [x[:4] for x in _bild(quelle)] == [x[:4] for x in neu_vorher]
    for sid in (ziel, quelle):
        await _dateien_da(sid)
    assert aufnahmen.sitzung(quelle)["status"] == "completed" and not aufnahmen.sitzung(quelle)["ziel_id"]
    assert [w.von for w in werbestellen.stellen(werbestellen.Bezug.aufnahme(quelle))] == [1.0]
    assert [e["title"] for e in (await aufnahmen.titelliste(aufnahmen.sitzung(ziel)))["entries"]] == ["A", "B"]
    assert [x[1] for x in (await feinschnitt_lauf.analyse_lesen(ziel)).wechsel] == ["A", "B"]


async def test_abbruch_mittendrin_geht_weiter(client, tmp_path, monkeypatch):
    ziel, quelle = await _paar(tmp_path)
    echt, zahl = ablage().verschieben, [0]

    async def stockend(alt, neu):
        zahl[0] += 1
        if zahl[0] == 2:
            raise AblageFehler("weg")
        return await echt(alt, neu)

    monkeypatch.setattr(ablage(), "verschieben", stockend)
    with pytest.raises(AblageFehler):
        await anhaengen(quelle)
    assert len(aufnahmen.segmente(ziel)) == 3 and len(aufnahmen.segmente(quelle)) == 2
    for sid in (ziel, quelle):
        await _dateien_da(sid)
    assert await nachholen() >= 1
    assert len(aufnahmen.segmente(ziel)) == 5 and [z["title"] for z in aufnahmen.segmente(ziel)][2:] == [z[1] for z in _bild(ziel)][2:]
    starts = [z["start_ms"] for z in aufnahmen.segmente(ziel)]
    assert starts == sorted(starts)
    assert len([x for x in schritte(gegenstand("sitzung", ziel).schluessel) if x["was"].startswith("Angehängt")]) == 1


async def test_loeschen_nimmt_angehaengtes_mit(client, tmp_path):
    ziel, quelle = await _paar(tmp_path)
    await anhaengen(quelle)
    assert client.delete(f"/api/recording/sessions/{ziel}").status_code == 200
    assert aufnahmen.sitzung(quelle) is None and aufnahmen.sitzung(ziel) is None


async def test_geht_nicht_und_bleibt_eine_eigene(client, tmp_path):
    ziel, quelle = await _paar(tmp_path)
    with db_session() as conn:
        conn.execute("UPDATE segments SET file_path = replace(file_path, '.mp3', '.aac') WHERE session_id = ?", (ziel,))
    with pytest.raises(AufnahmeFehler, match="anderen Format"):
        await anhaengen(quelle)
    assert len(aufnahmen.segmente(quelle)) == 3 and aufnahmen.sitzung(ziel)["status"] == "completed"
    with pytest.raises(AufnahmeFehler, match="anderen Sender"):
        ziel_pruefen(ziel, "u2")
    with pytest.raises(AufnahmeFehler, match="gibt es nicht mehr"):
        ziel_pruefen("weg", "u1")
    feinschnitt_lauf.status_setzen(ziel, "feinschnitt")
    with pytest.raises(AufnahmeFehler, match="gerade geschnitten"):
        ziel_pruefen(ziel, "u1")
    feinschnitt_lauf.status_setzen(ziel, "completed")


async def test_weiter_aufnehmen_im_ganzen_ablauf(client, mp3, monkeypatch, tmp_path):  # noqa: F811
    from app.routers import hls as wege
    from app.services.hls_buffer import HLSBufferService
    monkeypatch.setattr(recorder_modul, "MIN_SEGMENT_SECONDS", 0)
    rec = recorder_modul.rec_manager

    async def aufnehmen(sender, ziel=None):
        e = await rec.start("s1", "Probesender", sender.adresse(), 64, ziel_id=ziel)
        assert e["success"], e
        for _ in range(200):
            if rec.active_session.ton_s >= 12.0:
                break
            await asyncio.sleep(0.05)
        await rec.stop()
        await rec.feinschnitt_abwarten()
        return e["session_id"]

    async with Sender(mp3 * 4, DREI, takt_s=0.05) as sender:
        ziel = await aufnehmen(sender)
        erste = [z["title"] for z in aufnahmen.segmente(ziel)]
        quelle = await aufnehmen(sender, ziel)
        assert [z["title"] for z in aufnahmen.segmente(ziel)] == erste + erste and aufnahmen.sitzung(quelle)["status"] == "angehaengt"
        assert (await rec.start("s2", "Anderer", sender.adresse(), 64, ziel_id=ziel)) == {"success": False, "error": "Die Aufnahme ist von einem anderen Sender"}
        # und einen fertigen Titel aus dem Puffer dazu
        puffer = HLSBufferService(str(tmp_path / "hls"))
        monkeypatch.setattr(wege, "hls_buffer", puffer)
        await puffer.start("s1", "Probesender", sender.adresse(), bitrate=64)
        for _ in range(300):
            if puffer.empfang and puffer.empfang.jetzt_s >= 18:
                break
            await asyncio.sleep(0.05)
        b = puffer.abschnitte()[1]
        await wege.titel_sichern(wege.Titelwunsch(bei_s=(b["von"] + b["bis"]) / 2, ziel=ziel))
        assert [z["title"] for z in aufnahmen.segmente(ziel)] == [*erste, *erste, "B - Zwei"] and puffer.abschnitte()[1]["gesichert"]
        await puffer.stop()
    await _dateien_da(ziel)
    assert modul.ANGEHAENGT == "angehaengt"
