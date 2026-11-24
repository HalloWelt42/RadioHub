"""Platz der Endablage (RAD-135): gezeigt wird der der Kellerwolke, nie der lokale der Zwischenstände."""

from __future__ import annotations

from types import SimpleNamespace

from appkern.kellerwolke import Kellerwolke, NichtErreichbar

from app.ablage import Platz, SpeicherAblage, ablage
from app.ablage import kellerwolke as kw


async def test_zahlen_kommen_aus_der_ablage(client):
    assert isinstance(ablage(), SpeicherAblage)
    s = client.get("/api/recordings/stats").json()
    assert (s["frei_bytes"], s["gesamt_bytes"]) == (10 * 1024**4, 20 * 1024**4) and "disk_free_gb" not in s
    z = client.get("/api/storage/ablage").json()
    assert z["frei_bytes"] == 10 * 1024**4 and z["verbunden"]
    assert client.get("/api/podcasts/storage/stats").json()["frei_bytes"] == 10 * 1024**4


async def test_kellerwolke_nennt_den_platz_und_fehlt_er_ist_er_unbekannt():
    a = kw.KellerwolkeAblage(Kellerwolke("https://kw.test", "kw_app_x"), "Apps/RadioHub", 0)
    gefragt = []

    async def speicher():
        gefragt.append(1)
        if len(gefragt) > 1:
            raise NichtErreichbar("weg")
        return SimpleNamespace(gesamt=24, frei=14)
    a._sofort.speicher = speicher
    assert await a.platz() == Platz(24, 14) and await a.platz() == Platz(24, 14) and len(gefragt) == 1, "kurz gemerkt"
    a._platz_seit -= kw.PLATZ_GILT_S + 1
    assert await a.platz() == Platz(None, None)
