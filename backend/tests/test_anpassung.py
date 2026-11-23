"""RAD-12: Anpassung der Senderliste als Liste von Kennungen (SHA-256 der uuid): PRO nimmt getroffene Sender aus dem
Bestand (Abgleich und Aufbereitung), das Werkzeug der statischen Liste lässt sie weg."""

from __future__ import annotations

import pytest

from app.database import db_session
from app.senderdaten import Verzeichnisdatensatz
from app.senderdaten import anpassung as baustein
from app.senderdaten.anpassung import Anpassung, aus_text, kennung
from app.services.senderquelle import abgleich, dienst
from app.werkzeuge import statische_liste as sl
from test_senderquelle import PRAEFIX, _abfrage, _abgleich, _datensatz, _sender, radio, verzeichnis  # noqa: F401 (Fixtures)


def test_kennungen_lesen_und_treffen():
    a = aus_text(f"\n{kennung('Uuid-Eins')}\n\n")
    assert a.trifft("uuid-eins") and a.trifft(" UUID-EINS ")       # wie das Verzeichnis: ohne Groß und klein
    assert not a.trifft("uuid-zwei") and not a.trifft("")
    with pytest.raises(ValueError, match="Zeile 2"):
        aus_text(f"{kennung('a')}\nuuid-im-klartext\n")


def test_liste_der_app_ist_gueltig():
    baustein.laden.cache_clear()
    assert baustein.laden().kennungen, "die Liste der App ist da und lesbar"


def test_statische_liste_ohne_getroffene():
    def satz(k: str) -> Verzeichnisdatensatz:
        return Verzeichnisdatensatz.model_validate({"stationuuid": k, "name": k, "url": f"https://strom.test/{k}", "lastcheckok": 1})
    liste, gelesen = sl.liste_bauen([satz("a"), satz("b"), satz("c")], "datenbank",
                                    anpassung=Anpassung(kennungen=frozenset({kennung("b")})))
    assert gelesen == 3 and liste.kopf.anzahl == 2


def test_eigene_anpassung_der_webversion_trifft_rechner():
    def satz(k: str, url: str, aufgeloest: str = "") -> Verzeichnisdatensatz:
        return Verzeichnisdatensatz.model_validate({"stationuuid": k, "name": k, "url": url, "url_resolved": aufgeloest, "lastcheckok": 1})
    a = Anpassung(kennungen=frozenset({kennung("welle.test")}))
    assert sl.trifft(a, satz("a", "https://welle.test/x")) and sl.trifft(a, satz("b", "https://Eis.Welle.test:8443/x"))
    assert sl.trifft(a, satz("c", "https://liste.test/x.pls", "https://eis2.welle.test/x")), "auch die aufgelöste Adresse"
    assert not sl.trifft(a, satz("d", "https://andere-welle.test/x")) and not sl.trifft(a, satz("e", "https://strom.test/welle.test"))
    assert not sl.trifft(a, satz("f", "kaputt")) and not sl.trifft(a, satz("g", "https://[kaputt/"))
    assert list(sl.rechnernamen("https://a.b.test/")) == ["a.b.test", "b.test"], "nie die oberste Ebene"


def test_eigene_anpassung_fehlt_nie_unbemerkt(tmp_path, monkeypatch):
    datei = tmp_path / "anpassung.txt"
    with pytest.raises(SystemExit, match="nicht gefunden"):
        sl.eigene_anpassung(datei)
    datei.write_text("\n")
    with pytest.raises(SystemExit, match="leer"):
        sl.eigene_anpassung(datei)
    datei.write_text("welle.test\n")
    with pytest.raises(SystemExit, match="Zeile 1"):
        sl.eigene_anpassung(datei)
    datei.write_text(kennung("welle.test"))
    monkeypatch.setattr(sl, "EIGENE_ANPASSUNG", datei)
    assert sl.eigene_anpassung().trifft("welle.test")


@pytest.fixture
def angepasst(monkeypatch):
    """Die App mit eigener Liste; Ergebnis: die Menge, in die eine Prüfung ihre uuids legt."""
    uuids: set[str] = set()
    monkeypatch.setattr(dienst, "anpassung", lambda: Anpassung(kennungen=frozenset(kennung(u) for u in uuids)))
    return uuids


def test_aufbereiten_nimmt_getroffene_aus_dem_bestand(radio, angepasst):
    bleibt = _sender("Bleibt")
    weg = _sender("Weg")
    radio.portal.call(dienst.aufbereiten)
    assert radio.portal.call(dienst.aufbereitung_noetig) is None
    angepasst.add(weg)
    assert radio.portal.call(dienst.aufbereitung_noetig) == "anpassung", "neue Kennungen: der Start bereitet auf"
    radio.portal.call(dienst.aufbereiten)
    with db_session() as conn:
        da = {z[0] for z in conn.execute("SELECT uuid FROM stations WHERE uuid LIKE ?", (PRAEFIX + "%",))}
        im_index = {z[0] for z in conn.execute("SELECT uuid FROM sender_index WHERE uuid LIKE ?", (PRAEFIX + "%",))}
    assert da == im_index == {bleibt}
    assert [e["uuid"] for e in _abfrage(radio, nur_erreichbar=False)["eintraege"]] == [bleibt]
    assert radio.portal.call(dienst.aufbereitung_noetig) is None


def test_abgleich_speichert_getroffene_nicht(verzeichnis, monkeypatch, angepasst):
    c, liste, _ = verzeichnis
    monkeypatch.setattr(abgleich, "MINDESTANTEIL", 0)
    a, b = PRAEFIX + "a", PRAEFIX + "b"
    angepasst.add(b)
    liste += [_datensatz(a, "Eins"), _datensatz(b, "Zwei")]
    assert _abgleich(c)["zustand"] == "fertig"
    with db_session() as conn:
        assert {z[0] for z in conn.execute("SELECT uuid FROM stations WHERE uuid LIKE ?", (PRAEFIX + "%",))} == {a}
