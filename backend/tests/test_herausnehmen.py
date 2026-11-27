"""Stücke aus einer fertigen Aufnahme herausnehmen (RAD-150): alles danach rückt nach vorn, was im Bereich lag, fällt weg."""

import json

from test_aufnahmen import _mit_stuecken
from test_anhaengen import _setzen

from app.ablage import ablage
from app.services import feinschnitt_lauf, werbestellen
from app.services.aufnahmen import aufnahmen
from app.services.feinschnitt_lauf import Analyse
from app.services.herausnehmen import Zeitachse, analyse_ruecken, stuecke_herausnehmen


def test_zeitachse():
    achse = Zeitachse([(8000, 12000), (4000, 6000), (5000, 7000)])            # überlappend und ungeordnet
    assert achse.bereiche == [(4000, 7000), (8000, 12000)]
    assert [achse.neu(t) for t in (0, 3999, 4000, 6500, 7000, 7500, 8000, 11999, 12000, 15000)] == \
           [0, 3999, 4000, 4000, 4000, 4500, 5000, 5000, 5000, 8000]
    assert achse.weg(4000) and achse.weg(11999) and not achse.weg(7000) and not achse.weg(12000)


def test_analyse_rueckt_im_abschnitt():
    achse = Zeitachse([(10_000, 20_000)])
    a = Analyse(ab=5.0, dauer=30.0, wechsel=[(0.0, "A", False), (5.0, "B", False), (15.0, "C", False)],
                stillen=[(4.8, 5.2), (14.8, 15.2)], pegel=[(1.0, -20.0), (8.0, -18.0), (20.0, -19.0)], werbung=[(18.0, 25.0, "Spot")])
    r = analyse_ruecken(a, achse)
    assert r.ab == 5.0 and r.dauer == 20.0
    assert r.wechsel == [(0.0, "A", False), (5.0, "C", False)]                   # B lag im herausgenommenen Bereich
    assert r.stillen == [(4.8, 5.0), (5.0, 5.2)]                                 # die Stille an der Naht bleibt
    assert r.pegel == [(1.0, -20.0), (10.0, -19.0)]
    assert r.werbung == [(8.0, 15.0, "Spot")]


async def test_herausnehmen_rueckt_alles_nach(client, tmp_path):
    s = await _mit_stuecken(tmp_path, 4)
    zeilen = aufnahmen.segmente(s["id"])
    laenge = [z["duration_ms"] for z in zeilen]
    pfad = f"{s['file_path']}/Titelliste.json"
    await ablage().schreiben(pfad, json.dumps({"total_audio_bytes": 4000, "entries": [
        {"t": z["start_ms"], "b": i * 1000, "title": z["title"]} for i, z in enumerate(zeilen)]}).encode())
    _setzen(s["id"], meta_file_path=pfad)
    ende_2 = zeilen[1]["end_ms"]
    werbestellen.ersetzen(werbestellen.Bezug.aufnahme(s["id"]), "sendedaten",
                          [werbestellen.Neu(von=zeilen[1]["start_ms"] / 1000 + 0.5, bis=ende_2 / 1000 - 0.5, text="im Titel"),
                           werbestellen.Neu(von=zeilen[2]["start_ms"] / 1000 + 0.5, bis=zeilen[2]["start_ms"] / 1000 + 3.5, text="danach")])
    await feinschnitt_lauf.analyse_ablegen(s["id"], Analyse(dauer=sum(laenge) / 1000, wechsel=[(z["start_ms"] / 1000, z["title"], False) for z in zeilen]))

    assert await stuecke_herausnehmen(s["id"], [zeilen[1]]) == 1

    neu = aufnahmen.segmente(s["id"])
    assert [z["title"] for z in neu] == ["Titel 1", "Titel 3", "Titel 4"]
    assert [z["segment_index"] for z in neu] == [0, 1, 2]
    assert [z["start_ms"] for z in neu] == [0, laenge[0], laenge[0] + laenge[2]]                 # lückenlos
    assert all(a["end_ms"] == b["start_ms"] for a, b in zip(neu, neu[1:]))
    assert await ablage().eintrag(zeilen[1]["file_path"]) is None
    sitzung = aufnahmen.sitzung(s["id"])
    assert abs(sitzung["duration"] - (sum(laenge) - laenge[1]) / 1000) < 0.01
    marken = werbestellen.stellen(werbestellen.Bezug.aufnahme(s["id"]))
    assert [(m.text, round(m.von, 2)) for m in marken] == [("danach", round(laenge[0] / 1000 + 0.5, 2))]
    liste = await aufnahmen.titelliste(sitzung)
    assert [(e["title"], e["t"]) for e in liste["entries"]] == [("Titel 1", 0), ("Titel 3", laenge[0]), ("Titel 4", laenge[0] + laenge[2])]
    a = await feinschnitt_lauf.analyse_lesen(s["id"])
    assert [(t, x) for t, x, _ in a.wechsel] == [(0.0, "Titel 1"), (laenge[0] / 1000, "Titel 3"), ((laenge[0] + laenge[2]) / 1000, "Titel 4")]
