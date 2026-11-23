"""Welche Sender der Lernlauf nachts hört (HELF-256): was man selbst hört, die Favoriten, und darüber hinaus ähnliche Sender
(gleiche Genres, Sprache, Land) und die bekanntesten der eigenen Länder. Werbung läuft senderübergreifend: was nachts bei einem
anderen Sender gefunden wird, ist am Tag beim eigenen schon bekannt.

Die Liste geht an den Propaganda-Filter; der entscheidet, wen er wann hört. Ausgeblendete Sender kommen nie hinein.
"""

from __future__ import annotations

import json
import logging
from collections import Counter

from pydantic import BaseModel

from ..database import db_session
from . import hoerverlauf
from . import propagandafilter as pf

logger = logging.getLogger("radiohub.lernliste")

AEHNLICHE, BEKANNTE = 80, 80
VORBILDER = 25                      # aus so vielen Sendern wird der eigene Geschmack gelesen
JE_GENRE = 400                      # so viele bekannte Sender je Genre werden verglichen


class Lernsender(BaseModel):
    quelle: str
    name: str
    adresse: str
    grund: str
    gewicht: float = 1.0


SPALTEN = """SELECT i.uuid, s.name, COALESCE(NULLIF(u.custom_url, ''), NULLIF(s.url_resolved, ''), s.url) AS adresse, i.genres, i.sprachen,
       i.land, i.stimmen, i.favorit FROM sender_index i JOIN stations s ON s.uuid = i.uuid
       LEFT JOIN station_custom_urls u ON u.station_uuid = i.uuid"""
BRAUCHBAR = " i.sichtbar = 1 AND i.erreichbar = 1 AND COALESCE(s.hls, 0) = 0 "


def _tauglich(z) -> bool:
    adresse = (z["adresse"] or "").lower().split("?")[0]
    return adresse.startswith(("http://", "https://")) and not adresse.endswith((".m3u8", ".m3u", ".pls"))


def _sprachen(z) -> list[str]:
    return [x["code"] if isinstance(x, dict) and x.get("code") else str(x) for x in json.loads(z["sprachen"] or "[]")]


def zusammenstellen() -> list[Lernsender]:
    stunden = hoerverlauf.stunden()
    liste: dict[str, Lernsender] = {}
    with db_session() as c:
        eigene = c.execute(f"{SPALTEN} WHERE i.favorit = 1 OR i.uuid IN ({','.join('?' * len(stunden))})", list(stunden)).fetchall()
        eigene = [z for z in eigene if _tauglich(z)]
        for z in eigene:
            gehoert = stunden.get(z["uuid"], 0.0)
            liste[z["uuid"]] = Lernsender(quelle=z["uuid"], name=(z["name"] or "").strip(), adresse=z["adresse"],
                                          grund="gehoert" if gehoert >= 0.25 else "favorit", gewicht=round(min(gehoert, 20.0), 1))
        # der eigene Geschmack: was man hört, zählt nach Stunden, ein Favorit wie eine Stunde
        vorbilder = sorted(eigene, key=lambda z: -(stunden.get(z["uuid"], 0.0) + z["favorit"]))[:VORBILDER]
        genres: Counter[str] = Counter()
        sprachen: Counter[str] = Counter()
        laender: Counter[str] = Counter()
        for z in vorbilder:
            w = min(stunden.get(z["uuid"], 0.0), 10.0) + z["favorit"]
            for g in json.loads(z["genres"] or "[]"):
                genres[g] += w
            for s in _sprachen(z):
                sprachen[s] += w
            laender[z["land"]] += w
        punkte: dict[str, tuple[float, object]] = {}
        gesamt = sum(genres.values()) or 1.0
        for genre, _ in genres.most_common(8):
            for z in c.execute(f"{SPALTEN} JOIN sender_genre g ON g.nr = i.nr AND g.genre = ? WHERE {BRAUCHBAR} AND i.vertreter = 1"
                               " ORDER BY i.stimmen DESC LIMIT ?", (genre, JE_GENRE)):
                if z["uuid"] in liste or z["uuid"] in punkte or not _tauglich(z):
                    continue
                naehe = sum(genres[g] for g in json.loads(z["genres"] or "[]")) / gesamt
                heimat = (1.0 if z["land"] in laender else 0.0) + (1.0 if any(s in sprachen for s in _sprachen(z)) else 0.0)
                punkte[z["uuid"]] = (naehe * (0.3 + heimat) * (1 + min(z["stimmen"], 5000) / 2500), z)
        for wert, z in sorted(punkte.values(), key=lambda x: -x[0])[:AEHNLICHE]:
            liste[z["uuid"]] = Lernsender(quelle=z["uuid"], name=(z["name"] or "").strip(), adresse=z["adresse"], grund="aehnlich", gewicht=round(wert, 2))
        orte = {l: w for l, w in laender.most_common(4) if l} or {"DE": 1.0}
        for land, w in orte.items():                  # so viele bekannte je Land, wie man aus ihm hört
            anzahl = max(5, round(BEKANNTE * w / sum(orte.values())))
            bekannte = c.execute(f"{SPALTEN} WHERE {BRAUCHBAR} AND i.vertreter = 1 AND i.land = ? ORDER BY i.stimmen DESC LIMIT ?",
                                 (land, anzahl * 4)).fetchall()
            for z in [z for z in bekannte if z["uuid"] not in liste and _tauglich(z)][:anzahl]:
                liste[z["uuid"]] = Lernsender(quelle=z["uuid"], name=(z["name"] or "").strip(), adresse=z["adresse"], grund="bekannt")
    return list(liste.values())


async def weitergeben() -> int:
    """Die Liste an den Filter; liefert, wie viele Sender. Wirft FilterFehler."""
    liste = zusammenstellen()
    if liste:                                        # eine leere Liste (noch kein Senderbestand) ließe alles ruhen
        await pf.fragen("PUT", "lernlauf/sender", json=[s.model_dump() for s in liste])
    return len(liste)
