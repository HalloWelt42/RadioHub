"""Übergabe zwischen Geräten im Radio (RAD-18, RAD-96): was ein Gerät meldet und was bei Holen, Dorthin und Steuern
mitreist.

Den Vermittler stellt der Appkern (appkern.uebergabe); hier stehen nur die Modelle des Radios. Ein Paket trägt die
Quelle so, wie die Oberfläche sie zum Abspielen braucht (Sender, Folge mit Abo, Aufnahme), ohne lange Texte; die
Oberfläche des empfangenden Geräts spielt sie mit denselben Wegen wie einen Klick in der Liste.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from appkern.uebergabe import Vermittler

Quellart = Literal["sender", "folge", "aufnahme"]


class RadioZustand(BaseModel):
    """Was ein Gerät gerade spielt, so knapp, wie die Geräteliste es zeigt"""
    art: Quellart
    titel: str = Field("", max_length=300)
    untertitel: str = Field("", max_length=300)
    laeuft: bool = False
    #: für die Fernsteuerung (RAD-96): uuid des Senders, Bild der Quelle, Lautstärke
    kennung: str = Field("", max_length=64)
    bild: str = Field("", max_length=2000)
    lautstaerke: Optional[int] = Field(None, ge=0, le=100)


class _Verweis(BaseModel):
    """Die Angaben der Oberfläche reisen unverändert mit (sie stammen aus der App selbst)"""
    model_config = ConfigDict(extra="allow")


class SenderVerweis(_Verweis):
    uuid: str = Field(min_length=1, max_length=64)


class FolgeVerweis(_Verweis):
    id: int


class AufnahmeVerweis(_Verweis):
    playUrl: str = Field(min_length=1, max_length=2000)


class RadioPaket(BaseModel):
    art: Quellart
    sender: Optional[SenderVerweis] = None
    folge: Optional[FolgeVerweis] = None
    podcast: Optional[_Verweis] = None
    aufnahme: Optional[AufnahmeVerweis] = None
    stelle: float = Field(0, ge=0)

    @model_validator(mode="after")
    def _quelle_da(self) -> "RadioPaket":
        if getattr(self, self.art) is None:
            raise ValueError(f"Paket der Art {self.art} ohne {self.art}")
        return self


vermittler: Vermittler[RadioZustand, RadioPaket] = Vermittler(RadioZustand, RadioPaket)
