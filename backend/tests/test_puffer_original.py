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
