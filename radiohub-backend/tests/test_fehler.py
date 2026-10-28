"""Behobene Fehler: Timeshift startet die Aufnahme richtig, HLS-Nachholen legt nichts doppelt ab."""

from types import SimpleNamespace

from backend.services import timeshift_buffer as puffer
from backend.services.recorder import rec_manager


async def test_timeshift_startet_aufnahme_mit_await(monkeypatch):
    aufrufe = []

    async def start(**daten):
        aufrufe.append(daten)
        return {"success": True, "session_id": "rec_probe"}

    monkeypatch.setattr(rec_manager, "start", start)
    monkeypatch.setattr(puffer, "session", SimpleNamespace(station_uuid="u", station_name="Welle",
                                                            stream_url="http://welle.test", bitrate=128))
    ergebnis = await puffer.convert_to_recording()
    assert ergebnis == {"success": True, "recording_session_id": "rec_probe"}
    assert aufrufe[0]["station_name"] == "Welle"


async def test_nachholen_nach_teilweisem_ablegen_legt_nichts_doppelt_ab(speicher, tmp_path):
    from datetime import datetime
    from backend.ablage import orte
    from backend.config import get_arbeit_dir
    from backend.database import db_session
    from backend.services.aufnahmen import aufnahmen
    from conftest import ton

    sid = "hlsrec_probe_doppelt"
    with db_session() as c:
        c.execute("INSERT INTO sessions (id, station_name, start_time, file_path, status) VALUES (?, ?, ?, ?, 'interrupted')",
                  (sid, "Doppelfunk", datetime(2026, 1, 2).isoformat(), orte.aufnahmeordner("Doppelfunk", "2026-01-02T00:00:00")))
    arbeit = get_arbeit_dir("aufnahmen", sid)
    erstes = ton(arbeit / "teil_000.mp3", 1)
    await aufnahmen.teil_ablegen(sid, 0, "Erstes", 0, 1000, erstes)   # vor dem Abbruch schon abgelegt
    ton(arbeit / "teil_001.mp3", 1)                                    # liegt noch
    await aufnahmen.liegengebliebene_ablegen()
    assert [s["segment_index"] for s in aufnahmen.segmente(sid)] == [0, 1]
