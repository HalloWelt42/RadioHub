"""Werbung aus den Sendedaten (RAD-33): die Formate aus angaben.toml an echten Angaben aus dem Versuch vom 21.11.2026,
Werbestellen einer Sitzung (Spot beim Verbinden, Spots im Programm, Wechsel der Kennung) und die Grenze an der Stille,
die ffmpeg im Zeitversatz mitmeldet."""

from __future__ import annotations

import asyncio
import subprocess

from app.sendewerbung.angaben import lesen
from app.sendewerbung.sitzung import Sitzungswerbung
from test_stromleser import Sender

FFH = "StreamTitle='';StreamUrl='';adw_ad='true';durationMilliseconds='15046';adId='198927';insertionType='preroll';"
OTTO = ("StreamTitle='ANTENNE BAYERN - Wir lieben Bayern, wir lieben Musik';AdCreativeId='199103';"
        "AdTitle='OTTO_BF26_Audio_15s  -6dBfs - SENDEKOPIE-320kbps';Advertiser='otto.de';';")
ADAC = ("StreamTitle='OLDIE ANTENNE - Die Hits der 80er & 90er';AdCreativeId='196022';"
        "AdTitle='F230804_ADAC_Funk_TierischGuenstig_20s';Advertiser='adac.de';';")
VODAFONE = ("StreamTitle='OLDIE ANTENNE - Die Hits der 80er & 90er';AdCreativeId='198182';"
            "AdTitle='SIMon_Blackweek26_FUNK_99GB_15s_-6dB';Advertiser='vodafone.de';';")
OLDIE = "StreamTitle='OLDIE ANTENNE - Die Hits der 80er & 90er und die besten Oldies aller Zeiten!';"
LAUT = ["StreamTitle='mediamarkt.de - Ein bisschen Verbraucherinformationen ...';StreamUrl='0';",
        "StreamTitle='mediamarkt.de - ...  schon fast die Hälfte geschafft ...';StreamUrl='0';",
        "StreamTitle='mediamarkt.de - ...  zweite Halbzeit ...';StreamUrl='0';",
        "StreamTitle='mediamarkt.de - ...  gleich geht's los mit laut.fm/mangoradio ...';StreamUrl='0';"]
LIED = "StreamTitle='Aronchupa, Little Sis Nora - Little Swing';StreamUrl='2155156';"


def test_formate_an_echten_angaben():
    ffh = lesen(FFH)
    assert (ffh.format, ffh.kennung, ffh.dauer_ms, ffh.beim_verbinden, ffh.ende) == ("adswizz", "198927", 15046, True, "dauer")
    otto = lesen(OTTO)
    assert (otto.format, otto.kennung, otto.werbender, otto.ende) == ("creative", "199103", "otto.de", "wechsel")
    assert otto.titel.startswith("OTTO_BF26_Audio_15s")
    assert {(w.format, w.kennung) for w in map(lesen, LAUT)} == {("titel", "mediamarkt.de")}
    assert lesen("StreamTitle='Kurze Werbepause - Wirklich kurz';StreamUrl='5388535';").format == "werbepause"
    for kein in (LIED, OLDIE, "StreamTitle='I don't wanna wait / David Guetta & OneRepublic';json='{}';",
                 "StreamTitle='MANGORADIO - Nachrichten';StreamUrl='1';", "StreamTitle='';StreamUrl='';"):
        assert lesen(kein) is None, kein


def test_spot_beim_verbinden_mit_laenge_und_stille():
    w = Sitzungswerbung()
    w.angabe(FFH, 1.0)                                        # erste Angabe nach dem ersten Block: Spot ab 0
    w.angabe("StreamTitle='Du hörst HIT RADIO FFH';StreamUrl='107180030';", 16.0)
    (s,) = w.stellen
    assert (s.von, s.von_aus, s.bis, s.bis_aus, s.beim_verbinden) == (0.0, "verbinden", 15.046, "dauer", True)
    w.stille_zeile("[silencedetect @ 0x1] silence_start: 15.003")
    w.stille_zeile("[silencedetect @ 0x1] silence_end: 15.071 | silence_duration: 0.068")
    assert (s.bis, s.bis_aus) == (15.071, "stille")           # die Stille gehört noch zur Werbung


def test_spots_im_programm_enden_mit_dem_wechsel():
    w = Sitzungswerbung()
    w.angabe(OLDIE, 1.0)
    for t in (82.0, 83.0, 84.0):
        w.angabe(ADAC, t)                                     # dieselbe Kennung wiederholt sich je Block
    w.angabe(VODAFONE, 102.0)                                 # der nächste Spot beendet den vorigen
    assert w.stellen[-1].bis is None                          # offen bis zum nächsten Wechsel
    w.angabe(OLDIE, 117.0)
    assert [(s.werbender, s.von, s.bis, s.von_aus) for s in w.stellen] == [
        ("adac.de", 82.0, 102.0, "angabe"), ("vodafone.de", 102.0, 117.0, "angabe")]
    w.stille(81.6, 81.65)                                     # Stille kurz vor dem Spot: der Anfang rückt dorthin
    w.stille(101.95, 102.02)
    w.stille(119.0, 119.1)                                    # zu weit weg (über 1,5 s): bleibt die Angabe
    assert [(s.von, s.bis) for s in w.stellen] == [(81.6, 102.02), (101.95, 117.0)]
    assert [s.werbender for s in w.im_fenster(110.0)] == ["vodafone.de"]


def test_werbung_im_titel_ein_spot_ueber_mehrere_angaben():
    w = Sitzungswerbung()
    for i, roh in enumerate(LAUT):
        w.angabe(roh, 1.0 + i * 5)
    w.angabe(LIED, 21.0)
    assert [(s.werbender, s.von, s.bis, s.format) for s in w.stellen] == [("mediamarkt.de", 0.0, 21.0, "titel")]


async def test_zeitversatz_meldet_werbestelle_mit_grenze_an_der_stille(tmp_path, monkeypatch):
    """Ein nachgestellter Sender: 3 s Spot, 0,3 s digitale Stille, dann Programm; die Angabe kündigt 3000 ms an.
    Die Stelle endet am Ende der Stille, die ffmpeg im Zeitversatz meldet."""
    from app.services import stromleser as sl
    from app.services.hls_buffer import HLSBufferService
    monkeypatch.setattr(sl, "NEU_VERBINDEN_PAUSE_S", 0.0)
    datei = tmp_path / "sender.mp3"
    subprocess.run(["ffmpeg", "-y", "-v", "quiet", "-f", "lavfi", "-i", "sine=frequency=880:duration=3",
                    "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono:d=0.3", "-f", "lavfi", "-i", "sine=frequency=440:duration=20",
                    "-filter_complex", "[0][1][2]concat=n=3:v=0:a=1", "-c:a", "libmp3lame", "-b:a", "64k", str(datei)], check=True)
    spot = FFH.replace("15046", "3000")
    puffer = HLSBufferService(str(tmp_path / "hls"))
    async with Sender(datei.read_bytes(), {0: spot, 8: LIED}, takt_s=0.05) as sender:
        assert (await puffer.start("s1", "Probesender", sender.adresse(), bitrate=64))["status"] == "started"
        for _ in range(100):
            stellen = puffer.get_status()["werbestellen"]
            if stellen and stellen[0]["bis_aus"] == "stille":
                break
            await asyncio.sleep(0.1)
        await puffer.stop()
    (s,) = stellen
    assert (s["von"], s["von_aus"], s["bis_aus"], s["kennung"]) == (0.0, "verbinden", "stille", "198927")
    assert abs(s["bis"] - 3.3) < 0.1, s                        # Ende der Stille nach dem Spot
