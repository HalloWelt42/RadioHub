"""Codec, Bitrate und Qualitätsstufe. Die gemessene Bitrate gilt vor der Angabe des Verzeichnisses (Vorgabe 3); das
Verzeichnis führt manche Bitraten in bit/s statt kbit/s (332 Sender in der Sicherung vom 16.11.2026) oder mit
unmöglichen Werten, beides wird hier erkannt.

Stufen (Entwurf RAD-3): verlustfrei (FLAC, auch Ogg-FLAC); hoch ab 128 kbit/s bei AAC, Opus und Ogg Vorbis, ab 256 bei
MP3 und unbekanntem Codec; mittel ab 64 bzw. 96; darunter niedrig; ohne Bitrate unbekannt."""
from __future__ import annotations

from .modelle import Qualitaet

UNBEKANNT = "unbekannt"

# Schreibweisen des Verzeichnisses und der Messung -> Codec der Oberfläche
_CODECS = {
    "MP3": "MP3", "MPEG": "MP3", "MPEG3": "MP3",
    "AAC": "AAC", "AAC+": "AAC", "AACP": "AAC", "HE-AAC": "AAC", "MP4": "AAC", "M4A": "AAC", "FLV": "AAC",
    "OGG": "OGG", "VORBIS": "OGG",
    "OPUS": "OPUS",
    "FLAC": "FLAC",
    "WMA": "WMA",
}
_EFFIZIENT = {"AAC", "OPUS", "OGG"}
# Höchste glaubhafte Bitrate je verlustbehaftetem Codec (kbit/s); darüber ist die Angabe unbrauchbar
_OBERGRENZE = {"MP3": 320, "AAC": 576, "OPUS": 510, "WMA": 640}
_OGG_VERLUSTFREI_AB = 700       # Ogg mit dieser Bitrate ist kein Vorbis, sondern Ogg-FLAC
_UNBEKANNT_BIS = 640            # ohne Codec sagt eine höhere Bitrate nichts (oft Bild und Ton)


def codec(roh: str) -> str:
    """Codec in einheitlicher Form: ohne Videoanteil ("AAC,H.264"), Schreibweisen zusammengefasst, sonst "unbekannt"."""
    teile = [t.strip().upper() for t in (roh or "").split(",") if t.strip()]
    ton = [t for t in teile if not t.startswith(("H.26", "H26", "VP", "AV1"))]
    if not ton or ton[0] in ("UNKNOWN", "UNBEKANNT", ""):
        return UNBEKANNT
    return _CODECS.get(ton[0], ton[0])


def kbps_aus_verzeichnis(bitrate: int, codec_: str) -> int | None:
    """Bitrate des Verzeichnisses in kbit/s: Werte in bit/s (ab 8000) werden umgerechnet, unmögliche verworfen."""
    if not bitrate or bitrate <= 0:
        return None
    if bitrate >= 8000:
        kbps = round(bitrate / 1000)
        return kbps if 8 <= kbps <= 4000 else None
    grenze = _OBERGRENZE.get(codec_)
    if grenze and bitrate > grenze:
        return None
    return bitrate


def stufe(codec_: str, kbps: int | None) -> Qualitaet:
    if codec_ == "FLAC":
        return "verlustfrei"
    if not kbps or (codec_ == UNBEKANNT and kbps > _UNBEKANNT_BIS):
        return "unbekannt"
    if codec_ == "OGG" and kbps >= _OGG_VERLUSTFREI_AB:
        return "verlustfrei"
    hoch, mittel = (128, 64) if codec_ in _EFFIZIENT else (256, 96)
    if kbps >= hoch:
        return "hoch"
    if kbps >= mittel:
        return "mittel"
    return "niedrig"
