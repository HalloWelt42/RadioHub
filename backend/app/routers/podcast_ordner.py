"""
Ordner der Podcast-Abos (RAD-23): eigene Gruppen in der Seitenleiste, untereinander in ihrer Reihenfolge, ein Abo in
höchstens einem Ordner. Einen Ordner zu löschen nimmt nur die Gruppierung: seine Abos stehen danach wieder lose.
Eigener Pfad (/api/podcast-ordner), damit er nicht mit /api/podcasts/{podcast_id} kollidiert.
"""
from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..database import db_session

router = APIRouter(prefix="/api/podcast-ordner", tags=["podcasts"])


class OrdnerNeu(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)


class OrdnerAenderung(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=80)
    offen: Optional[bool] = None


class Reihenfolge(BaseModel):
    ids: List[str]


class Zuordnung(BaseModel):
    ordner_id: Optional[str] = None


def _ordner(r) -> dict:
    return {"id": r["id"], "name": r["name"], "reihenfolge": r["reihenfolge"], "offen": bool(r["offen"])}


@router.get("")
async def liste():
    with db_session() as conn:
        return {"ordner": [_ordner(r) for r in conn.execute("SELECT * FROM podcast_ordner ORDER BY reihenfolge, name")]}


@router.post("")
async def anlegen(neu: OrdnerNeu):
    """Neuer Ordner am Ende der Reihe."""
    with db_session() as conn:
        ende = conn.execute("SELECT COALESCE(MAX(reihenfolge), -1) + 1 FROM podcast_ordner").fetchone()[0]
        kennung = uuid.uuid4().hex
        conn.execute("INSERT INTO podcast_ordner (id, name, reihenfolge) VALUES (?, ?, ?)", (kennung, neu.name.strip(), ende))
        return _ordner(conn.execute("SELECT * FROM podcast_ordner WHERE id = ?", (kennung,)).fetchone())


@router.put("/reihenfolge")
async def ordnen(r: Reihenfolge):
    with db_session() as conn:
        for i, kennung in enumerate(r.ids):
            conn.execute("UPDATE podcast_ordner SET reihenfolge = ? WHERE id = ?", (i, kennung))
    return {"success": True}


@router.put("/abo/{podcast_id}")
async def zuordnen(podcast_id: int, z: Zuordnung):
    """Abo in einen Ordner legen oder (ordner_id leer) wieder lose."""
    with db_session() as conn:
        if z.ordner_id and not conn.execute("SELECT 1 FROM podcast_ordner WHERE id = ?", (z.ordner_id,)).fetchone():
            raise HTTPException(404, "Ordner nicht gefunden")
        c = conn.execute("UPDATE podcast_subscriptions SET ordner_id = ? WHERE id = ?", (z.ordner_id or None, podcast_id))
        if c.rowcount == 0:
            raise HTTPException(404, "Podcast nicht gefunden")
    return {"success": True}


@router.put("/{ordner_id}")
async def aendern(ordner_id: str, a: OrdnerAenderung):
    with db_session() as conn:
        if a.name is not None:
            conn.execute("UPDATE podcast_ordner SET name = ? WHERE id = ?", (a.name.strip(), ordner_id))
        if a.offen is not None:
            conn.execute("UPDATE podcast_ordner SET offen = ? WHERE id = ?", (int(a.offen), ordner_id))
        r = conn.execute("SELECT * FROM podcast_ordner WHERE id = ?", (ordner_id,)).fetchone()
        if not r:
            raise HTTPException(404, "Ordner nicht gefunden")
        return _ordner(r)


@router.delete("/{ordner_id}")
async def loeschen(ordner_id: str):
    """Nur die Gruppierung löschen: die Abos des Ordners stehen danach lose (nichts an den Abos geht verloren)."""
    with db_session() as conn:
        geloest = conn.execute("UPDATE podcast_subscriptions SET ordner_id = NULL WHERE ordner_id = ?", (ordner_id,)).rowcount
        if conn.execute("DELETE FROM podcast_ordner WHERE id = ?", (ordner_id,)).rowcount == 0:
            raise HTTPException(404, "Ordner nicht gefunden")
    return {"success": True, "geloest": geloest}
