"""Die ganze Kellerwolke für Aufnahmen und Schnitt (RAD-17): Ebene für Ebene nur Ordner und Audiodateien, Ton mit
Bereich, fehlende Freigabe als lesbare Meldung."""

from app.ablage import KeineAblage, wolke_setzen
from app.ablage.port import KeinRecht


async def test_ebene_zeigt_ordner_und_nur_audio(client, wolke_speicher):
    await wolke_speicher.schreiben("Interviews/Gespräch.mp3", b"a" * 50)
    await wolke_speicher.schreiben("Interviews/Notiz.txt", b"t")
    await wolke_speicher.schreiben("Interviews/2025/Rückblick.flac", b"f" * 10)
    oben = client.get("/api/wolke/ebene").json()
    assert [o["name"] for o in oben["ordner"]] == ["Interviews"] and oben["kette"] == [] and oben["schreibbar"] is False
    e = client.get("/api/wolke/ebene", params={"pfad": "Interviews"}).json()
    assert [o["pfad"] for o in e["ordner"]] == ["Interviews/2025"]
    assert [d["name"] for d in e["dateien"]] == ["Gespräch.mp3"] and e["gesamt"] == 1      # die Notiz nicht
    assert e["kette"] == [{"name": "Interviews", "pfad": "Interviews"}] and e["schreibbar"] is True
    teil = client.get("/api/wolke/ton", params={"pfad": "Interviews/Gespräch.mp3"}, headers={"Range": "bytes=0-9"})
    assert teil.status_code == 206 and teil.content == b"a" * 10
    assert client.get("/api/wolke/ton", params={"pfad": "Interviews/Notiz.txt"}).status_code == 415
    assert client.get("/api/wolke/ebene", params={"pfad": "../x"}).status_code == 422


def test_ohne_freigabe_sagt_es_die_antwort(client):
    class OhneRecht(KeineAblage):
        async def liste(self, ordner):
            raise KeinRecht("kein Recht")
    wolke_setzen(OhneRecht("x"))
    antwort = client.get("/api/wolke/ebene")
    assert antwort.status_code == 403 and "Alles lesen" in antwort.json()["detail"]
