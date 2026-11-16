"""Einstellungen der Ablage: Wurzelordner und Geduld, aus den Einstellungen des RadioHub (`einstellungen`).

Adresse, App-Schlüssel und Zertifikatsstelle der Kellerwolke gehören dem Zugang des Gerüsts (Grundeinstellungen des
Appkerns); die Ablage bekommt diesen Zugang beim Einrichten (`ablage.einrichten`).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..einstellungen import AppEinstellungen

VORGABE_WURZEL = "Apps/RadioHub"
VORGABE_GEDULD_S = 900.0


class AblageEinstellungen(BaseModel):
    wurzel: str = Field(VORGABE_WURZEL, description="Wurzelordner in der Kellerwolke")
    geduld_s: float = Field(VORGABE_GEDULD_S, ge=0, description="Wartezeit beim Ablegen, wenn die Kellerwolke fehlt")

    @classmethod
    def aus(cls, stand: AppEinstellungen) -> AblageEinstellungen:
        return cls(wurzel=stand.kellerwolke_wurzel.strip() or VORGABE_WURZEL, geduld_s=stand.kellerwolke_geduld_s)
