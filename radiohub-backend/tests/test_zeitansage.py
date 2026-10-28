"""Zeitansage: Zahlwörter, Bausteine, Erzeugen über die (nachgestellte) Vertonung, Ausliefern aus der Ablage."""

import json
import subprocess

import httpx

from backend.ablage import AblageEinstellungen
from backend.services.zeitansage import Zeitansage, ZeitansageEinstellungen, ansage, bausteine, stunde_text, zahlwort


def test_zahlwoerter_und_bausteine():
    assert [zahlwort(n) for n in (1, 11, 16, 17, 21, 30, 34, 57)] == [
        "eins", "elf", "sechzehn", "siebzehn", "einundzwanzig", "dreißig", "vierunddreißig", "siebenundfünfzig"]
    assert stunde_text(0) == "null Uhr" and stunde_text(1) == "ein Uhr" and stunde_text(17) == "siebzehn Uhr"
    assert len(bausteine()) == 84
    assert ansage(5, 34) == ["es-ist", "stunde-05", "minute-34"]
    assert ansage(7, 0) == ["es-ist", "stunde-07"]


def _wav() -> bytes:
    return subprocess.run(["ffmpeg", "-v", "quiet", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono:d=0.2", "-f", "lavfi",
                           "-i", "sine=frequency=300:duration=0.4:sample_rate=24000", "-filter_complex",
                           "[0][1][0]concat=n=3:v=0:a=1", "-f", "wav", "-"], capture_output=True, check=True).stdout


async def test_erzeugen_legt_fehlende_bausteine_ab(speicher, tmp_path, client):
    schluessel = tmp_path / "schluessel"
    schluessel.write_text("kw_app_probe")
    wav = _wav()
    anfragen = []

    def vertonung(request: httpx.Request) -> httpx.Response:
        anfragen.append(request)
        assert request.headers["Authorization"] == "Bearer kw_app_probe"
        return httpx.Response(200, content=wav)

    await speicher.schreiben("Zeitansage/es-ist.mp3", b"schon da")
    e = ZeitansageEinstellungen(adresse="https://vertonung.test", stimme="stimme-1",
                                ablage=AblageEinstellungen(schluessel_datei=str(schluessel)))
    dienst = Zeitansage()
    assert await dienst.erzeugen(e, transport=httpx.MockTransport(vertonung)) == 83
    texte = [json.loads(a.content)["text"] for a in anfragen]
    assert len(texte) == 83 and "vierunddreißig" in texte and "ein Uhr" in texte and "Es ist" not in texte
    assert all(f"Zeitansage/{n}.mp3" in speicher.dateien for n in bausteine())
    kurz = speicher.dateien["Zeitansage/minute-34.mp3"]
    assert kurz[:3] == b"ID3" or kurz[:2] == b"\xff\xfb"
    assert (await dienst.stand())["fehlend"] == []
    antwort = client.get("/api/zeitansage/ton/minute-34")
    assert antwort.status_code == 200 and antwort.content == kurz
    assert client.get("/api/zeitansage/ton/boese").status_code == 404


async def test_ohne_einrichtung_meldet_sie_was_fehlt(speicher):
    dienst = Zeitansage()
    assert await dienst.erzeugen(ZeitansageEinstellungen()) == 0
    assert "nicht eingerichtet" in dienst.meldung
