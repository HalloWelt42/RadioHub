"""Zeitversatz mit Originalton (RAD-92): unverändert übernehmen, wenn das Format es erlaubt, sonst umwandeln"""
from datetime import datetime

from app.services.hls_buffer import KOPIERBAR, HLSBufferService, HLSSession


def _sitzung(**teil) -> HLSSession:
    return HLSSession(session_id="s", station_uuid="u", station_name="Sender", stream_url="http://x", start_time=datetime.now(),
                      **teil)


def test_original_kopiert_ohne_angleichen_und_neukodieren(tmp_path):
    puffer = HLSBufferService(str(tmp_path / "hls"))
    puffer.session = _sitzung(original=True, input_codec="mp3", output_bitrate=128)
    cmd = puffer._build_ffmpeg_cmd("http://x", aus_empfang=True, eingang_format="mp3")
    assert cmd[cmd.index("-c:a") + 1] == "copy"
    assert "-af" not in cmd and "-b:a" not in cmd and "-ar" not in cmd
    assert cmd[cmd.index("-hls_time") + 1] == "1"


def test_umgewandelt_wie_bisher_mit_angleichen(tmp_path):
    puffer = HLSBufferService(str(tmp_path / "hls"))
    puffer.session = _sitzung(original=False, output_bitrate=96)
    cmd = puffer._build_ffmpeg_cmd("http://x", aus_empfang=True, eingang_format="aac")
    assert cmd[cmd.index("-c:a") + 1] == "aac" and cmd[cmd.index("-b:a") + 1] == "96k"
    assert any(t.startswith("loudnorm") for t in cmd)


def test_nur_mp3_und_aac_lassen_sich_unveraendert_uebernehmen():
    assert {"mp3", "aac"} == set(KOPIERBAR)
    assert "ogg" not in KOPIERBAR and "flac" not in KOPIERBAR


async def test_start_waehrend_des_beendens_behaelt_seinen_puffer(tmp_path, monkeypatch):
    """RAD-130: Beenden und Starten laufen nacheinander, ein verspätetes Ende trifft keine neuere Sitzung, überholte Starts entfallen."""
    import asyncio
    puffer = HLSBufferService(str(tmp_path / "hls"))
    gestartet: list[str] = []

    async def starten(adresse: str) -> dict:
        await puffer._beenden()
        await asyncio.sleep(0.02)
        puffer.session = _sitzung()
        puffer.session.session_id = puffer._neue_kennung()
        puffer.session.stream_url = adresse
        gestartet.append(adresse)
        return {"status": "started", "session_id": puffer.session.session_id}
    echt = puffer._strom_stoppen

    async def langsam() -> None:
        await asyncio.sleep(0.05)
        await echt()
    monkeypatch.setattr(puffer, "_starten", starten)
    monkeypatch.setattr(puffer, "_strom_stoppen", langsam)
    eins = await puffer.start("a")
    ende = asyncio.create_task(puffer.stop(eins["session_id"]))
    await asyncio.sleep(0.01)                                   # mitten im Beenden kommt der nächste Start
    zwei = await puffer.start("b")
    assert (await ende)["status"] == "stopped" and puffer.session and puffer.session.session_id == zwei["session_id"] != eins["session_id"]
    assert (await puffer.stop(eins["session_id"]))["status"] == "not_active" and puffer.session, "ein spätes Ende trifft nicht"
    antworten = await asyncio.gather(puffer.start("c"), puffer.start("d"), puffer.start("e"))
    assert [a["status"] for a in antworten] == ["superseded", "superseded", "started"] or gestartet[-1] == "e"
    assert puffer.session.stream_url == "e"
    assert (await puffer.stop())["status"] == "stopped" and puffer.session is None


async def test_beenden_wartet_nicht_auf_ffmpeg_im_lesen(tmp_path):
    """RAD-130: ffmpeg hängt im Lesen von stdin; erst dessen Ende lässt es gleich aufhören."""
    import asyncio
    import time
    puffer = HLSBufferService(str(tmp_path / "hls"))
    puffer.session = _sitzung(original=True, input_codec="mp3")
    puffer._ensure_buffer_dir()
    puffer._ffmpeg_process = await asyncio.create_subprocess_exec(
        *puffer._build_ffmpeg_cmd("http://x", aus_empfang=True, eingang_format="mp3"), stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE)
    await asyncio.sleep(0.5)
    t = time.monotonic()
    assert (await puffer.stop())["status"] == "stopped"
    assert time.monotonic() - t < 1.5
