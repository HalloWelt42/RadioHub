"""Zeitansage: Zahlwörter, Bausteine, Erzeugen über die (nachgestellte) Vertonung, Ausliefern aus der Ablage."""

import json
import subprocess

import httpx

from app.services.zeitansage import Zeitansage, ZeitansageEinstellungen, ansage, bausteine, stunde_text, zahlwort


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


async def test_erzeugen_legt_fehlende_bausteine_ab(speicher, client):
    wav = _wav()
    anfragen = []

    def vertonung(request: httpx.Request) -> httpx.Response:
        anfragen.append(request)
        assert request.headers["Authorization"] == "Bearer kw_app_probe"
        return httpx.Response(200, content=wav)

    await speicher.schreiben("Zeitansage/katalog-sohee/es-ist.mp3", b"schon da")
    e = ZeitansageEinstellungen(adresse="https://vertonung.test", stimme="katalog:sohee", schluessel="kw_app_probe")
    dienst = Zeitansage()
    assert await dienst.erzeugen(e, transport=httpx.MockTransport(vertonung)) == 83
    texte = [json.loads(a.content)["text"] for a in anfragen]
    assert {json.dumps(json.loads(a.content)["stimme"]) for a in anfragen} == {'{"art": "katalog", "name": "sohee"}'}
    assert {json.loads(a.content)["sprache"] for a in anfragen} == {"de"}
    assert len(texte) == 83 and "vierunddreißig" in texte and "ein Uhr" in texte and "Es ist" not in texte
    assert all(f"Zeitansage/katalog-sohee/{n}.mp3" in speicher.dateien for n in bausteine())
    kurz = speicher.dateien["Zeitansage/katalog-sohee/minute-34.mp3"]
    assert kurz[:3] == b"ID3" or kurz[:2] == b"\xff\xfb"
    assert (await dienst.stand("katalog:sohee"))["fehlend"] == []
    assert len((await dienst.stand("7ce9880d-0000-4000-8000-000000000000"))["fehlend"]) == 84   # andere Stimme, eigener Satz
    antwort = client.get("/api/zeitansage/ton/minute-34")                                      # Vorgabe: katalog:sohee
    assert antwort.status_code == 200 and antwort.content == kurz
    assert client.get("/api/zeitansage/ton/boese").status_code == 404


async def test_ohne_einrichtung_meldet_sie_was_fehlt(speicher):
    dienst = Zeitansage()
    assert await dienst.erzeugen(ZeitansageEinstellungen()) == 0
    assert "nicht eingerichtet" in dienst.meldung


def test_private_stimme_als_klon_und_eigener_ordner():
    from app.ablage import orte
    from app.services.zeitansage import stimme_der_app
    privat = ZeitansageEinstellungen(stimme="7ce9880d-9f61-4220-ae2b-648076764afd")
    assert stimme_der_app(privat) == {"art": "klon", "knoten_id": "7ce9880d-9f61-4220-ae2b-648076764afd"}
    assert stimme_der_app(ZeitansageEinstellungen(stimme="katalog:sohee")) == {"art": "katalog", "name": "sohee"}
    assert orte.zeitansage("katalog:sohee", "es-ist") == "Zeitansage/katalog-sohee/es-ist.mp3"
    assert orte.zeitansage_ordner("../x") == "Zeitansage/---x"                             # nie außerhalb des Ordners


async def test_auswahl_der_zeitstimme_aus_der_vertonung(monkeypatch):
    from types import SimpleNamespace
    from appkern.verbund import VerbundFehler
    from app.services import zeitstimmen

    class Verbund:
        async def anfrage(self, methode, adresse, pfad, *, params, **_):
            assert (methode, adresse, pfad) == ("GET", "https://vertonung.test", "/api/v1/stimmen")
            if params["bereich"] == "privat":
                raise VerbundFehler("nicht freigegeben", 403)
            return httpx.Response(200, json=[{"id": "katalog:sohee", "name": "sohee"}, {"id": "katalog:ryan", "name": "ryan"}])

    monkeypatch.setattr(zeitstimmen, "einstellungen_stand", lambda: SimpleNamespace(vertonung_adresse="https://vertonung.test/"))
    a = await zeitstimmen.angebot(Verbund())
    assert [o.wert for o in a.optionen] == ["katalog:sohee", "katalog:ryan"] and a.eigener_wert is False and a.stand == "2 Stimmen"
    monkeypatch.setattr(zeitstimmen, "einstellungen_stand", lambda: SimpleNamespace(vertonung_adresse=""))
    assert (await zeitstimmen.angebot(Verbund())).optionen == []
