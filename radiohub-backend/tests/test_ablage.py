"""Vertrag der Ablage: jeder Adapter verhält sich gleich (Speicher immer, Kellerwolke beim Probelauf)."""

from __future__ import annotations

import os
import uuid

import pytest

from backend.ablage import AblageEinstellungen, Belegt, KeineAblage, NichtEingerichtet, SpeicherAblage, einrichten
from backend.ablage import orte
from backend.ablage.port import sauberer_pfad

PROBE = os.environ.get("RADIOHUB_PROBE_KELLERWOLKE") == "1"


@pytest.fixture(params=["speicher"] + (["kellerwolke"] if PROBE else []))
async def adapter(request):
    if request.param == "speicher":
        yield SpeicherAblage()
        return
    from backend.ablage.kellerwolke import KellerwolkeAblage
    e = AblageEinstellungen.aus_umgebung()
    probe = KellerwolkeAblage.aus_einstellungen(e.model_copy(update={"wurzel": f"{e.wurzel}/Probe-{uuid.uuid4().hex[:8]}"}))
    try:
        yield probe
    finally:
        await probe.loeschen("")
        await probe.schliessen()


async def test_ablegen_lesen_und_bereich(adapter, tmp_path):
    quelle = tmp_path / "a.mp3"
    quelle.write_bytes(b"0123456789")
    eintrag = await adapter.ablegen("Aufnahmen/SWR3/2026-10-28 14-00-05/001 Ä Titel.mp3", quelle)
    assert eintrag.groesse == 10 and not eintrag.ist_ordner and eintrag.name == "001 Ä Titel.mp3"
    assert await adapter.lesen_ganz(eintrag.pfad) == b"0123456789"
    assert await adapter.lesen_ganz(eintrag.pfad, 2, 5) == b"2345"
    assert (await adapter.eintrag("Aufnahmen/SWR3")).ist_ordner


async def test_ablegen_auf_vorhandene_datei_ist_neue_version(adapter, tmp_path):
    await adapter.schreiben("Podcasts/Abo/x.json", b"alt")
    await adapter.schreiben("Podcasts/Abo/x.json", b"neu!")
    assert await adapter.lesen_ganz("Podcasts/Abo/x.json") == b"neu!"


async def test_liste_ordner_vor_dateien_und_alle_dateien(adapter):
    await adapter.schreiben("Aufnahmen/B/2026/b.mp3", b"b")
    await adapter.schreiben("Aufnahmen/a.mp3", b"a")
    namen = [e.name for e in await adapter.liste("Aufnahmen")]
    assert namen == ["B", "a.mp3"]
    assert sorted(e.pfad for e in await adapter.alle_dateien("Aufnahmen")) == ["Aufnahmen/B/2026/b.mp3",
                                                                               "Aufnahmen/a.mp3"]
    assert await adapter.liste("Gibt/es/nicht") == []


async def test_verschieben_und_belegt(adapter):
    await adapter.schreiben("Aufnahmen/SWR3/1/a.mp3", b"a")
    await adapter.schreiben("Aufnahmen/Konzerte/x.mp3", b"x")
    await adapter.verschieben("Aufnahmen/SWR3/1", "Aufnahmen/Konzerte/SWR3/1")
    assert await adapter.eintrag("Aufnahmen/SWR3/1") is None
    assert await adapter.lesen_ganz("Aufnahmen/Konzerte/SWR3/1/a.mp3") == b"a"
    with pytest.raises(Belegt):
        await adapter.verschieben("Aufnahmen/Konzerte/x.mp3", "Aufnahmen/Konzerte/SWR3/1/a.mp3")


async def test_loeschen_geht_in_den_papierkorb(adapter):
    await adapter.schreiben("Aufnahmen/S/1/a.mp3", b"a")
    assert await adapter.loeschen("Aufnahmen/S/1") is True
    assert await adapter.eintrag("Aufnahmen/S/1/a.mp3") is None
    assert await adapter.loeschen("Aufnahmen/S/1") is False
    if isinstance(adapter, SpeicherAblage):
        assert adapter.papierkorb == ["Aufnahmen/S/1/a.mp3"]


async def test_freier_pfad_zaehlt_hoch(adapter):
    await adapter.schreiben("Podcasts/Abo/2026-10-01 Folge.mp3", b"1")
    assert await adapter.freier_pfad("Podcasts/Abo/2026-10-01 Folge.mp3") == "Podcasts/Abo/2026-10-01 Folge (2).mp3"
    assert await adapter.freier_pfad("Podcasts/Abo/neu.mp3") == "Podcasts/Abo/neu.mp3"


async def test_zustand(adapter):
    zustand = await adapter.zustand()
    assert zustand["verbunden"] is True


def test_pfade_ohne_ausbruch():
    assert sauberer_pfad("/Aufnahmen//SWR3/") == "Aufnahmen/SWR3"
    with pytest.raises(ValueError):
        sauberer_pfad("Aufnahmen/../../Apps/Anderes")


def test_orte_lesbar():
    ordner = orte.aufnahmeordner("SWR3: Pop/Rock", "2026-10-28T14:00:05", None)
    assert ordner == "Aufnahmen/SWR3 Pop Rock/2026-10-28 14-00-05"
    assert orte.aufnahmeordner("WDR 2", "2026-10-28T14:00:05", "Konzerte") == "Aufnahmen/Konzerte/WDR 2/2026-10-28 14-00-05"
    assert orte.stueck(ordner, 0, "Über / Grenzen", ".MP3") == f"{ordner}/001 Über Grenzen.mp3"
    assert orte.folge("Zeitfragen", "Folge 1: Anfang?", "2026-10-01 06:00:00", ".mp3") == \
        "Podcasts/Zeitfragen/2026-10-01 Folge 1 Anfang.mp3"


async def test_ohne_einstellungen_meldet_die_ablage_was_fehlt():
    ablage = einrichten(AblageEinstellungen())
    assert isinstance(ablage, KeineAblage)
    with pytest.raises(NichtEingerichtet):
        await ablage.liste("Aufnahmen")
    assert (await ablage.zustand())["verbunden"] is False


async def test_einstellungen_aus_der_umgebung(monkeypatch, tmp_path):
    schluessel = tmp_path / "schluessel"
    schluessel.write_text("kw_app_test\n")
    monkeypatch.setenv("RADIOHUB_KELLERWOLKE_ADRESSE", "https://kellerwolke.test:39280")
    monkeypatch.setenv("RADIOHUB_KELLERWOLKE_SCHLUESSEL", str(schluessel))
    monkeypatch.delenv("RADIOHUB_KELLERWOLKE_WURZEL", raising=False)
    e = AblageEinstellungen.aus_umgebung()
    assert e.eingerichtet and e.wurzel == "Apps/RadioHub"
    ablage = einrichten(e)
    assert "kw_app_test" not in repr(ablage)
    await ablage.schliessen()
