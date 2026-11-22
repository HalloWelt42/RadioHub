"""Werbung aus den Sendedaten je Sender (RAD-33): welche Sender Werbung ankündigen, die bekannten Spots eines Senders
und sein Schalter (überspringen oder ausgenommen), dazu die Marke Werbung (entfernbar, RAD-59). Die Einstellung für alle Sender (werbung_ueberspringen) liegt bei
den Einstellungen; die Werbestellen der laufenden Sitzung stehen im Status des Zeitversatzes (/api/hls/status)."""
from fastapi import APIRouter
from pydantic import BaseModel

from ..sendewerbung import spots

router = APIRouter(prefix="/api/sendewerbung", tags=["werbung"])


class Schalter(BaseModel):
    ueberspringen: bool


@router.get("")
def werbende() -> list[spots.SenderWerbung]:
    return spots.werbende()


@router.get("/{uuid}")
def steckbrief(uuid: str) -> spots.Steckbrief:
    return spots.steckbrief(uuid)


@router.put("/{uuid}")
def setzen(uuid: str, schalter: Schalter) -> spots.Steckbrief:
    spots.setzen(uuid, schalter.ueberspringen)
    return spots.steckbrief(uuid)


@router.delete("/{uuid}/marke")
def marke_entfernen(uuid: str) -> spots.Steckbrief:
    spots.marke_entfernen(uuid)
    return spots.steckbrief(uuid)
