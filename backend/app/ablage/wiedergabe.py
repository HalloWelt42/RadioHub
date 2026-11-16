"""Dateien aus der Ablage über HTTP ausliefern, mit Bereichsanfragen (Range), damit Spulen geht."""

from __future__ import annotations

import re
from urllib.parse import quote

from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse

from ..config import AUDIO_MIMETYPES
from . import ablage
from .port import Ablage

_BEREICH = re.compile(r"bytes=(\d*)-(\d*)$")


def bereich(kopf: str | None, groesse: int) -> tuple[int, int] | None:
    """(start, ende einschließlich) aus einem Range-Kopf; None ohne Kopf oder bei mehreren Bereichen."""
    if not kopf:
        return None
    treffer = _BEREICH.match(kopf.strip())
    if not treffer or (not treffer.group(1) and not treffer.group(2)):
        return None
    anfang, schluss = treffer.groups()
    if anfang == "":
        laenge = int(schluss)
        start, ende = max(groesse - laenge, 0), groesse - 1
    else:
        start = int(anfang)
        ende = min(int(schluss), groesse - 1) if schluss else groesse - 1
    if start >= groesse or start > ende:
        raise HTTPException(416, "Bereich außerhalb der Datei", headers={"Content-Range": f"bytes */{groesse}"})
    return start, ende


def inhaltstyp(dateiname: str) -> str:
    endung = "." + dateiname.rsplit(".", 1)[-1].lower() if "." in dateiname else ""
    return AUDIO_MIMETYPES.get(endung, "application/octet-stream")


async def ausliefern(pfad: str, request: Request | None = None, *, dateiname: str | None = None,
                     herunterladen: bool = False, quelle: Ablage | None = None) -> StreamingResponse:
    """Datei aus der Ablage als Antwort; mit Range-Kopf nur der Bereich (206)."""
    quelle = quelle or ablage()
    eintrag = await quelle.eintrag(pfad)
    if eintrag is None or eintrag.ist_ordner:
        raise HTTPException(404, "Datei nicht gefunden")
    name = dateiname or eintrag.name
    teil = bereich(request.headers.get("range") if request else None, eintrag.groesse)
    kopf = {"Accept-Ranges": "bytes"}
    art = "attachment" if herunterladen else "inline"
    kopf["Content-Disposition"] = f"{art}; filename*=UTF-8''{quote(name)}"
    if teil is None:
        kopf["Content-Length"] = str(eintrag.groesse)
        return StreamingResponse(quelle.lesen(pfad), media_type=inhaltstyp(name), headers=kopf)
    start, ende = teil
    kopf["Content-Length"] = str(ende - start + 1)
    kopf["Content-Range"] = f"bytes {start}-{ende}/{eintrag.groesse}"
    return StreamingResponse(quelle.lesen(pfad, start, ende), status_code=206, media_type=inhaltstyp(name),
                             headers=kopf)
