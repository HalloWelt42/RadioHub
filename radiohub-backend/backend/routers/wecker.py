"""
RadioHub v0.6.0 - Wecker

Wecker liegen in der Datenbank des RadioHub; ausgelöst werden sie in der Weckeransicht am Telefon (Querformat,
Seite offen), weil Web-Apps im Hintergrund nicht geweckt werden. Dazu der Ort für Sonnenauf- und -untergang
(Breite, Länge, Name) als Einstellung.
"""
import json
import os
import re
from typing import Literal, Optional

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from ..database import db_session
from ..services.config_service import config_service

router = APIRouter(prefix="/api/wecker", tags=["wecker"])


class WeckerDaten(BaseModel):
    aktiv: bool = True
    zeit: str = Field(..., description="HH:MM")
    tage: list[int] = Field(default_factory=lambda: [1, 2, 3, 4, 5], description="1 = Montag bis 7 = Sonntag")
    quelle: Literal["sender", "podcast"] = "sender"
    sender: Optional[dict] = Field(None, description="Sender wie in der Senderliste (uuid, name, url, favicon)")
    podcast_id: Optional[int] = None
    lautstaerke: int = Field(60, ge=5, le=100)
    anstieg_s: int = Field(60, ge=0, le=600)
    schlummern_min: int = Field(9, ge=1, le=60)

    @field_validator("zeit")
    @classmethod
    def _zeit(cls, wert: str) -> str:
        if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", wert):
            raise ValueError("Zeit als HH:MM")
        return wert

    @field_validator("tage")
    @classmethod
    def _tage(cls, wert: list[int]) -> list[int]:
        if any(t < 1 or t > 7 for t in wert):
            raise ValueError("Wochentage 1 bis 7")
        return sorted(set(wert))


def _aus_zeile(r) -> dict:
    return {"id": r["id"], "aktiv": bool(r["aktiv"]), "zeit": r["zeit"], "tage": json.loads(r["tage"] or "[]"),
            "quelle": r["quelle"], "sender": json.loads(r["sender_json"]) if r["sender_json"] else None,
            "podcast_id": r["podcast_id"], "lautstaerke": r["lautstaerke"], "anstieg_s": r["anstieg_s"],
            "schlummern_min": r["schlummern_min"]}


def _pruefen(d: WeckerDaten) -> None:
    if d.quelle == "sender" and not (d.sender and d.sender.get("uuid")):
        raise HTTPException(400, "Sender fehlt")
    if d.quelle == "podcast" and not d.podcast_id:
        raise HTTPException(400, "Podcast fehlt")


def _werte(d: WeckerDaten) -> tuple:
    return (int(d.aktiv), d.zeit, json.dumps(d.tage), d.quelle, json.dumps(d.sender) if d.sender else None,
            d.podcast_id, d.lautstaerke, d.anstieg_s, d.schlummern_min)


# --- Ort für Sonnenzeiten ------------------------------------------------------------------------------------------

class Ort(BaseModel):
    name: str = ""
    breite: Optional[float] = Field(None, ge=-90, le=90)
    laenge: Optional[float] = Field(None, ge=-180, le=180)


# Ortssuche über die hauseigene Kartensuche (OSM lokal); Adresse in RADIOHUB_ORTSSUCHE_ADRESSE, leer: keine Suche
ORTSSUCHE = os.environ.get("RADIOHUB_ORTSSUCHE_ADRESSE", "").strip().rstrip("/")


class Fundort(BaseModel):
    name: str
    art: str = ""
    breite: float
    laenge: float


@router.get("/orte")
async def orte_suchen(q: str = Query(..., min_length=2, max_length=100)) -> dict:
    """Orte zum Namen, für die Sonnenzeiten; nur Städte, Orte und Dörfer."""
    if not ORTSSUCHE:
        raise HTTPException(503, "Ortssuche nicht eingerichtet (RADIOHUB_ORTSSUCHE_ADRESSE)")
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            antwort = await c.get(f"{ORTSSUCHE}/api/v1/suche", params={"q": q, "limit": 20})
            antwort.raise_for_status()
    except httpx.HTTPError as f:
        raise HTTPException(502, f"Ortssuche nicht erreichbar: {f.__class__.__name__}") from f
    orte = [Fundort(name=e["name"], art=e.get("kind") or "", breite=e["lat"], laenge=e["lng"])
            for e in antwort.json().get("results", []) if e.get("category") == "ort"]
    return {"orte": orte[:8]}


@router.get("/ort")
async def ort_lesen():
    return Ort(name=config_service.get("ort_name") or "", breite=config_service.get("ort_breite"),
               laenge=config_service.get("ort_laenge"))


@router.put("/ort")
async def ort_setzen(ort: Ort):
    config_service.update({"ort_name": ort.name, "ort_breite": ort.breite, "ort_laenge": ort.laenge})
    return ort


# --- Wecker -------------------------------------------------------------------------------------------------------

@router.get("")
async def liste():
    with db_session() as conn:
        return {"wecker": [_aus_zeile(r) for r in conn.execute("SELECT * FROM wecker ORDER BY zeit, id")]}


@router.post("")
async def anlegen(d: WeckerDaten):
    _pruefen(d)
    with db_session() as conn:
        neu = conn.execute("""INSERT INTO wecker (aktiv, zeit, tage, quelle, sender_json, podcast_id, lautstaerke,
                              anstieg_s, schlummern_min) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", _werte(d)).lastrowid
        return _aus_zeile(conn.execute("SELECT * FROM wecker WHERE id = ?", (neu,)).fetchone())


@router.put("/{wecker_id}")
async def aendern(wecker_id: int, d: WeckerDaten):
    _pruefen(d)
    with db_session() as conn:
        c = conn.execute("""UPDATE wecker SET aktiv = ?, zeit = ?, tage = ?, quelle = ?, sender_json = ?, podcast_id = ?,
                            lautstaerke = ?, anstieg_s = ?, schlummern_min = ? WHERE id = ?""", (*_werte(d), wecker_id))
        if c.rowcount == 0:
            raise HTTPException(404, "Wecker nicht gefunden")
        return _aus_zeile(conn.execute("SELECT * FROM wecker WHERE id = ?", (wecker_id,)).fetchone())


@router.delete("/{wecker_id}")
async def loeschen(wecker_id: int):
    with db_session() as conn:
        if conn.execute("DELETE FROM wecker WHERE id = ?", (wecker_id,)).rowcount == 0:
            raise HTTPException(404, "Wecker nicht gefunden")
    return {"success": True}
