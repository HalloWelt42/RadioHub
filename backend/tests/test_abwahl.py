"""Titel während der Aufnahme abwählen (RAD-150): die Aufnahme läuft weiter, der Titel fehlt danach ganz; bis zum Stopp lässt er sich wieder
anwählen, auch der laufende."""

from test_stromleser import DREI, Sender, _puffer_bis, mp3  # noqa: F401 - Fixture

from app.routers import hls as wege
from app.services import recorder as recorder_modul
from app.services.aufnahmen import aufnahmen
from app.services.hls_buffer import HLSBufferService

async def test_abwaehlen_und_wieder_anwaehlen(client, mp3, tmp_path, monkeypatch):  # noqa: F811
    monkeypatch.setattr(recorder_modul, "MIN_SEGMENT_SECONDS", 0)
    rec = recorder_modul.rec_manager
    puffer = HLSBufferService(str(tmp_path / "hls"))
    monkeypatch.setattr(wege, "hls_buffer", puffer)
    async with Sender(mp3 * 6, DREI, takt_s=0.1) as sender:
        assert (await puffer.start("s1", "Probesender", sender.adresse(), bitrate=64))["status"] == "started"
        await _puffer_bis(puffer, 3.0)
        e = await rec.start("s1", "Probesender", sender.adresse(), 64)
        assert e["success"], e
        await _puffer_bis(puffer, 20.0)
        a, b, c = [x for x in puffer.abschnitte() if x["art"] == "titel"][:3]
        assert a["in_aufnahme"] and c["laufend"] and not a["abgewaehlt"]
        mitte = lambda x: (x["von"] + x["bis"]) / 2                                        # noqa: E731
        assert (await wege.abwaehlen(wege.Abwahl(bei_s=mitte(b))))["abgewaehlt"]
        await wege.abwaehlen(wege.Abwahl(bei_s=c["von"] + 1))                               # der laufende auch
        await wege.abwaehlen(wege.Abwahl(bei_s=mitte(a)))
        await wege.abwaehlen(wege.Abwahl(bei_s=mitte(a), an=False))                          # und zurück
        assert [x["abgewaehlt"] for x in puffer.abschnitte() if x["art"] == "titel"][:3] == [False, True, True]
        await _puffer_bis(puffer, 30.0)
        await rec.stop()
        await rec.feinschnitt_abwarten()
        await puffer.stop()
    titel = [z["title"] for z in aufnahmen.segmente(e["session_id"])]
    assert "B - Zwei" not in titel and "C - Drei" not in titel and titel[0] == "A - Eins", titel
    zeilen = aufnahmen.segmente(e["session_id"])
    assert [z["segment_index"] for z in zeilen] == list(range(len(zeilen)))
    assert zeilen[0]["start_ms"] == 0 and all(a["end_ms"] == b["start_ms"] for a, b in zip(zeilen, zeilen[1:]))  # lückenlos
    s = aufnahmen.sitzung(e["session_id"])
    assert abs(s["duration"] - sum(z["duration_ms"] for z in zeilen) / 1000) < 0.01

async def test_ohne_laufende_aufnahme_nichts_abzuwaehlen(client, mp3, tmp_path, monkeypatch):  # noqa: F811
    puffer = HLSBufferService(str(tmp_path / "hls"))
    monkeypatch.setattr(wege, "hls_buffer", puffer)
    async with Sender(mp3 * 3, DREI, takt_s=0.1) as sender:
        await puffer.start("s1", "Probesender", sender.adresse(), bitrate=64)
        await _puffer_bis(puffer, 10.0)
        assert not any(x["in_aufnahme"] for x in puffer.abschnitte())
        try:
            await wege.abwaehlen(wege.Abwahl(bei_s=2.0))
            raise AssertionError("ohne Aufnahme darf nichts abgewählt werden")
        except wege.HTTPException as f:
            assert f.status_code == 409
        await puffer.stop()
