"""Anschluss an den Propaganda-Filter (HELF-256): Vergleich zweier Fassungen als Auftrag mit Fortschritt, Fehler des
Filters, und die Quelle "vergleich" der Werbestellen nur für gespeicherte Folgen."""

from __future__ import annotations

import json

import httpx
import pytest

from app.database import db_session
from app.services import propagandafilter as pf
from app.services import werbestellen as ws
from test_podcasts import _folge

E = pf.FilterEinstellungen(adresse="https://filter.test", schluessel="kw_app_radiohub", abfragen_s=0)
ERGEBNIS = {"gleich": False, "verwertbar": True, "anteil_gemeinsam": 0.97, "nur_in_a": [{"von": 0.0, "bis": 30.12,
            "signatur": "s1"}, {"von": 1585.3, "bis": 1620.0, "signatur": None}], "nur_in_b": [], "hinweis": None}


async def _strom(*teile: bytes):
    for t in teile:
        yield t


def _filter(zustaende: list[dict], gesehen: dict) -> httpx.MockTransport:
    def antwort(r: httpx.Request) -> httpx.Response:
        assert r.headers["authorization"] == "Bearer kw_app_radiohub"
        if r.method == "POST":
            gesehen["koerper"] = r.read()
            gesehen["zweite"] = r.url.params["zweite"]
            gesehen["quelle"] = r.url.params["quelle"]
            return httpx.Response(202, json={"id": "a1", **zustaende.pop(0)})
        return httpx.Response(200, json={"id": "a1", **zustaende.pop(0)})
    return httpx.MockTransport(antwort)


async def test_vergleich_als_auftrag_mit_fortschritt():
    gesehen: dict = {}
    zustaende = [{"zustand": "wartet", "fortschritt": 0, "schritt": "wartet auf einen freien Platz"},
                 {"zustand": "laeuft", "fortschritt": 0.4, "schritt": "sucht A in B"},
                 {"zustand": "fertig", "fortschritt": 1, "schritt": "fertig", "ergebnis": ERGEBNIS}]
    gemeldet: list[tuple[float, str]] = []
    ergebnis = await pf.vergleichen(E, _strom(b"ID3", b"ton"), "https://feed.test/folge.mp3", "Podcast: Folge",
                                    lambda a, s: gemeldet.append((a, s)), transport=_filter(zustaende, gesehen))
    assert gesehen == {"koerper": b"ID3ton", "zweite": "https://feed.test/folge.mp3", "quelle": "Podcast: Folge"}
    assert gemeldet == [(0, "wartet auf einen freien Platz"), (0.4, "sucht A in B")]
    assert [(s.von, s.bis) for s in ergebnis.nur_in_a] == [(0.0, 30.12), (1585.3, 1620.0)]


async def test_fehler_des_filters():
    with pytest.raises(pf.FilterFehler, match="nicht eingerichtet"):
        await pf.vergleichen(pf.FilterEinstellungen(), _strom(b"x"), "https://feed.test/f.mp3", "")
    abgelehnt = httpx.MockTransport(lambda r: httpx.Response(403, json={"detail": "Die App RadioHub steht nicht auf der Liste"}))
    with pytest.raises(pf.FilterFehler, match="403.*nicht auf der Liste"):
        await pf.vergleichen(E, _strom(b"x"), "https://feed.test/f.mp3", "", transport=abgelehnt)
    gesehen: dict = {}
    zustaende = [{"zustand": "laeuft"}, {"zustand": "fehler", "fehler": "Anbieter antwortet mit 404"}]
    with pytest.raises(pf.FilterFehler, match="404"):
        await pf.vergleichen(E, _strom(b"x"), "https://feed.test/f.mp3", "", transport=_filter(zustaende, gesehen))


def _eingerichtet(monkeypatch, an: bool = True) -> None:
    monkeypatch.setattr(pf.FilterEinstellungen, "jetzt", classmethod(lambda cls: E if an else cls()))


async def test_quelle_vergleich_nur_fuer_gespeicherte_folgen(client, speicher, monkeypatch):
    folge = _folge("Wirtschaftsfunk", "Lobby-Gipfel")
    _eingerichtet(monkeypatch)
    assert client.get(f"/api/podcasts/episodes/{folge}/werbung").json()["quellen"] == []        # nicht gespeichert
    pfad = "Podcasts/Wirtschaftsfunk/Lobby-Gipfel.mp3"
    await speicher.schreiben(pfad, b"ID3ton")
    with db_session() as conn:
        conn.execute("UPDATE podcast_episodes SET is_downloaded = 1, local_path = ?, audio_url = 'https://feed.test/f.mp3' "
                     "WHERE id = ?", (pfad, folge))
    assert client.get(f"/api/podcasts/episodes/{folge}/werbung").json()["quellen"] == ["vergleich"]
    _eingerichtet(monkeypatch, False)
    assert client.get(f"/api/podcasts/episodes/{folge}/werbung").json()["quellen"] == []        # ohne Filter

    _eingerichtet(monkeypatch)
    gesehen: dict = {}

    async def vergleichen(e, fassung_a, zweite, quelle, melden):
        gesehen["a"] = b"".join([t async for t in fassung_a])
        gesehen["zweite"], gesehen["quelle"] = zweite, quelle
        melden(0.5, "sucht A in B")
        return pf.Vergleichsergebnis.model_validate(ERGEBNIS)
    monkeypatch.setattr(pf, "vergleichen", vergleichen)
    antwort = client.post(f"/api/podcasts/episodes/{folge}/werbung/suchen")
    ereignisse = [json.loads(z[6:]) for z in antwort.text.splitlines() if z.startswith("data: ")]
    assert ereignisse[-1] == {"type": "done", "gefunden": {"vergleich": 2}}, ereignisse
    assert any(e.get("message") == "Vergleich zweier Fassungen: sucht A in B (50%)" for e in ereignisse)
    assert gesehen == {"a": b"ID3ton", "zweite": "https://feed.test/f.mp3", "quelle": "Podcast: Lobby-Gipfel"}
    assert [(s.von, s.bis, s.herkunft) for s in ws.stellen(folge)] == [(0.0, 30.12, "vergleich"), (1585.3, 1620.0, "vergleich")]


async def test_gleiche_fassungen_ergeben_keine_stellen(speicher, monkeypatch):
    folge = _folge("Wirtschaftsfunk", "Ohne Werbung")
    _eingerichtet(monkeypatch)

    async def vergleichen(*_a, **_k):
        return pf.Vergleichsergebnis(gleich=True, verwertbar=True, hinweis="Beide Fassungen sind Byte für Byte gleich")
    monkeypatch.setattr(pf, "vergleichen", vergleichen)
    assert await ws.vergleich_suchen({"id": folge, "title": "x", "local_path": "p", "audio_url": "u"}, lambda *_: None) == []
