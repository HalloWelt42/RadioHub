"""Einstellungen der Ablage, aus der Umgebung (docker-compose.yml oder Shell).

    RADIOHUB_KELLERWOLKE_ADRESSE    Adresse der Kellerwolke, etwa https://192.168.178.49:39280
    RADIOHUB_KELLERWOLKE_SCHLUESSEL Pfad der Datei mit dem App-Schlüssel (Rechte 600, Inhalt nur der Schlüssel)
    RADIOHUB_KELLERWOLKE_WURZEL     Wurzelordner der Dateien in der Kellerwolke (Vorgabe Apps/RadioHub)
    RADIOHUB_KELLERWOLKE_CA         Zertifikatsstelle der Kellerwolke (rootCA.pem der Hausstelle), leer: nur die üblichen
    RADIOHUB_KELLERWOLKE_GEDULD_S   So lange wartet das Ablegen auf eine nicht erreichbare Kellerwolke (Vorgabe 900)

Der Schlüssel selbst steht nie in der Umgebung, nur der Pfad seiner Datei.
"""

from __future__ import annotations

import os

from pydantic import BaseModel, Field

VORGABE_WURZEL = "Apps/RadioHub"
VORGABE_GEDULD_S = 900.0


class AblageEinstellungen(BaseModel):
    adresse: str = Field("", description="Adresse der Kellerwolke")
    schluessel_datei: str = Field("", description="Pfad der Datei mit dem App-Schlüssel")
    wurzel: str = Field(VORGABE_WURZEL, description="Wurzelordner in der Kellerwolke")
    ca_datei: str = Field("", description="Zertifikatsstelle (PEM)")
    geduld_s: float = Field(VORGABE_GEDULD_S, ge=0, description="Wartezeit beim Ablegen, wenn die Kellerwolke fehlt")

    @property
    def eingerichtet(self) -> bool:
        return bool(self.adresse.strip() and self.schluessel_datei.strip())

    @classmethod
    def aus_umgebung(cls) -> AblageEinstellungen:
        umgebung = os.environ
        return cls(
            adresse=umgebung.get("RADIOHUB_KELLERWOLKE_ADRESSE", "").strip(),
            schluessel_datei=umgebung.get("RADIOHUB_KELLERWOLKE_SCHLUESSEL", "").strip(),
            wurzel=umgebung.get("RADIOHUB_KELLERWOLKE_WURZEL", "").strip() or VORGABE_WURZEL,
            ca_datei=umgebung.get("RADIOHUB_KELLERWOLKE_CA", "").strip(),
            geduld_s=float(umgebung.get("RADIOHUB_KELLERWOLKE_GEDULD_S", "") or VORGABE_GEDULD_S),
        )
