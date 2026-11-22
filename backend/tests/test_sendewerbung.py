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


NEUNZIGER = "90s90s - DIGITAL WEB"
VORLAUF = f"StreamTitle='{NEUNZIGER}';"
CRUSH = "StreamTitle='Jennifer Paige - Crush';"


def test_vorlauf_nur_als_erste_angabe_mit_dem_namen_des_senders():
    v = lesen(VORLAUF, NEUNZIGER, erste=True)
    assert (v.format, v.kennung, v.beim_verbinden, v.bestaetigen) == ("vorlauf", NEUNZIGER, True, "stille")
    assert lesen(VORLAUF, NEUNZIGER, erste=False) is None      # mitten im Programm: der Name ist kein Vorlauf
    assert lesen(VORLAUF, "", erste=True) is None              # ohne Namen im Kopf keine Aussage
    assert lesen(CRUSH, NEUNZIGER, erste=True) is None
    bob = "RADIO BOB - Livestream National"                     # Sonderzeichen im Namen zählen wörtlich
    assert lesen(f"StreamTitle='{bob}';", bob, erste=True).format == "vorlauf"
    assert lesen("StreamTitle='RADIO BOB - Livestream Nationalx';", bob, erste=True) is None


def test_vorlauf_endet_an_der_stille():
    """Echter Fall 90s90s 22.11.2026: Vorlauf 30 s, Stille 30,025 bis 30,072, erster Titel bei 30,4 s. FFmpeg meldet
    die Stille erst nach der Angabe (der Leser liest beim Verbinden voraus)."""
    w = Sitzungswerbung()
    w.sendername = NEUNZIGER
    w.angabe(VORLAUF, 0.34)
    w.angabe(CRUSH, 30.38)
    (s,) = w.stellen
    assert (s.von, s.bis, s.beim_verbinden) == (0.0, None, True)         # wartet auf die Stille
    w.ton_bis(29.0)
    w.stille(30.025, 30.072)
    assert (s.bis, s.bis_aus) == (30.072, "stille")
    w.ton_bis(40.0)
    assert w.stellen == [s] and not w.verworfen


def test_vorlauf_ohne_stille_war_nur_ein_spaeter_titel():
    """Echter Fall 90s90s 22.11.2026, gleichzeitige zweite Verbindung: kein Vorlauf, das Lied läuft schon, der Titel
    kommt erst bei 12,6 s. Ohne Stille dort wird die Stelle verworfen."""
    w = Sitzungswerbung()
    w.sendername = NEUNZIGER
    w.angabe(VORLAUF, 0.34)
    w.angabe(CRUSH, 12.62)
    w.ton_bis(13.5)
    assert len(w.stellen) == 1
    w.ton_bis(14.2)
    assert w.stellen == [] and [s.kennung for s in w.verworfen] == [NEUNZIGER]
    w.stille(20.0, 20.1)                                         # spätere Stille holt sie nicht zurück
    assert w.stellen == []


def test_vorlauf_endet_an_seiner_stille_auch_ohne_titel():
    """Echter Fall 90s90s 22.11.2026: der Name des Senders stand 258 s als Titel (bis zum zweiten Lied). Der Vorlauf
    endet an seiner Stille, ohne auf die nächste Angabe zu warten; die spätere Angabe ist ein gewöhnlicher Wechsel."""
    w = Sitzungswerbung()
    w.sendername = NEUNZIGER
    w.angabe(VORLAUF, 0.34)
    w.stille(2.0, 2.05)                                           # zu früh: noch im Spot
    (s,) = w.stellen
    assert s.bis is None
    w.stille(30.025, 30.072)
    assert (s.bis, s.bis_aus) == (30.072, "stille")
    w.angabe(CRUSH, 258.4)
    assert w.stellen == [s] and s.bis == 30.072


def test_vorlauf_ohne_stille_und_ohne_titel_faellt_nach_hoechstens_weg():
    w = Sitzungswerbung()
    w.sendername = NEUNZIGER
    w.angabe(VORLAUF, 0.34)
    w.ton_bis(50.0)
    assert len(w.stellen) == 1
    w.ton_bis(62.0)
    assert w.stellen == [] and len(w.verworfen) == 1
    w.angabe(CRUSH, 258.4)                                        # danach ein gewöhnlicher Titel
    assert w.stellen == []


def test_spot_beim_verbinden_mit_laenge_und_stille():
    w = Sitzungswerbung()
    w.angabe(FFH, 1.0)                                        # erste Angabe nach dem ersten Block: Spot ab 0
    w.angabe("StreamTitle='Du hörst HIT RADIO FFH';StreamUrl='107180030';", 16.0)
    (s,) = w.stellen
    assert (s.von, s.von_aus, s.bis, s.bis_aus, s.beim_verbinden) == (0.0, "verbinden", 15.046, "dauer", True)
    w.stille_zeile("[silencedetect @ 0x1] silence_start: 15.003")
    w.stille_zeile("[silencedetect @ 0x1] silence_end: 15.071 | silence_duration: 0.068")
    assert (s.bis, s.bis_aus) == (15.071, "stille")           # die Stille gehört noch zur Werbung


def test_spaeter_gemeldete_naehere_stille_gilt():
    """Echter Fall MANGORADIO 21.11.2026: der Spot endet laut Angabe bei 30,0; ffmpeg meldet erst die Stille bei 29,32
    bis 29,35, danach die nähere bei 29,77 bis 29,89. Es gilt die nähere, nicht die zuerst gemeldete."""
    w = Sitzungswerbung()
    w.angabe("StreamTitle='paypal.com - Ein bisschen Verbraucherinformationen ...';StreamUrl='0';", 1.0)
    w.angabe("StreamTitle='MANGORADIO - Nachrichten';StreamUrl='1';", 30.0)
    (s,) = w.stellen
    w.stille(29.32, 29.35)
    assert (s.bis, s.bis_aus) == (29.35, "stille")
    w.stille(29.77, 29.89)
    assert (s.bis, s.bis_aus) == (29.89, "stille")
    w.stille(30.97, 31.01)                                     # weiter weg als die gewählte: bleibt
    assert s.bis == 29.89


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
    w.stille(81.6, 81.65)                                     # Pause kurz vor dem Spot: er beginnt an ihrem Ende
    w.stille(101.95, 102.02)                                  # die Spots stoßen am Ende der Pause aneinander
    w.stille(119.0, 119.1)                                    # zu weit nach der Angabe (über 2 s): bleibt die Angabe
    assert [(s.von, s.bis) for s in w.stellen] == [(81.65, 102.02), (102.02, 117.0)]
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


def test_spots_zaehlen_und_schalter_je_sender(client):
    """Jede abgeschlossene Stelle zählt ihren Spot beim Sender; ein Fund macht den Sender werbend. Der Schalter je
    Sender nimmt ihn aus, die Einstellung für alle schaltet es überall ab."""
    from app.sendewerbung import spots
    w = Sitzungswerbung(bei_ende=lambda s: spots.merken("sender-1", s))
    w.angabe(FFH, 1.0)                                        # endet sofort (angekündigte Länge)
    w.angabe(OLDIE, 20.0)
    w.angabe(OTTO, 40.0)
    w.angabe(OLDIE, 55.0)                                     # beendet otto.de
    w.angabe(OTTO, 90.0)
    w.angabe(OLDIE, 105.0)                                    # derselbe Spot ein zweites Mal
    w.stille(104.6, 104.65)                                   # Stille am Ende: jetzt erst gezählt, mit genauer Länge
    w.angabe(OLDIE, 130.0)                                    # ohne Stille: gezählt, sobald das Fenster vorbei ist
    (eintrag,) = [e for e in client.get("/api/sendewerbung").json() if e["uuid"] == "sender-1"]
    assert (eintrag["uuid"], eintrag["spots"], eintrag["ueberspringen"]) == ("sender-1", 2, True)
    brief = client.get("/api/sendewerbung/sender-1").json()
    assert {(s["kennung"], s["anzahl"], s["dauer_ms"], s["beim_verbinden"]) for s in brief["liste"]} == {
        ("198927", 1, 15046, True), ("199103", 2, 14650, False)}                  # Länge der letzten Messung
    assert client.put("/api/sendewerbung/sender-1", json={"ueberspringen": False}).json()["ausgenommen"] is True
    assert spots.ueberspringt("sender-1") is False and spots.ueberspringt("anderer") is True
    assert client.put("/api/config", json={"updates": {"werbung_ueberspringen": False}}).status_code == 200
    assert spots.ueberspringt("anderer") is False
    client.put("/api/config", json={"updates": {"werbung_ueberspringen": True}})       # für die übrigen Tests zurück
    spots.setzen("sender-1", True)
    assert client.get("/api/sendewerbung/ohne-spots").json() == {
        "uuid": "ohne-spots", "name": "", "spots": 0, "zuletzt": None, "ueberspringen": True, "ausgenommen": False, "liste": []}
