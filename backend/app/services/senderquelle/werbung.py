"""Werbeverdacht neu gewichtet (Entscheidung 19): 189 von 190 Verdachtsfällen der Sicherung beruhten allein auf
`Cache-Control max-age=0`, darunter 24 Favoriten. Hier zählt jedes Zeichen der Werbeerkennung nach seiner Stärke; ein
schwaches allein (Cache-Kopf, fehlender ICY-Name) ergibt keinen Verdacht, erst zwei verschiedene schwache.

Stufen je Sender (sender_index.werbe_stufe): 4 eigene Entscheidung "sperren", 3 hoch (starkes Zeichen oder eigene
Markierung als Werbung), 2 mittel, 1 Verdacht, 0 keiner. Eine eigene Entscheidung "erlauben" oder ein Widerspruch
setzt auf 0. Grundlage sind die Tabellen station_ad_status (Erkennung und Entscheidungen) und station_tags (eigene
Bewertung "werbung" fließt in die Erkennung, Entscheidung 18)."""
from __future__ import annotations

import json
import sqlite3

STARK = frozenset({"URL_KNOWN_AD_NETWORK", "URL_SSAI_DOMAIN", "URL_AD_PATH_PATTERN", "DOMAIN_BLACKLIST_MATCH",
                   "HEADER_SSAI_MARKER", "HEADER_AD_SERVER_SIGNATURE", "REDIRECT_AD_INTERMEDIATE",
                   "MANUAL_USER_BLOCKED", "MANUAL_USER_REPORTED"})
MITTEL = frozenset({"URL_AGGREGATOR_RELAY", "URL_TRACKING_REDIRECT", "HEADER_TARGETING_COOKIES",
                    "HEADER_VARY_USERAGENT"})
SCHWACH = frozenset({"HEADER_SUSPICIOUSLY_SHORT_TTL", "HEADER_NO_ICY_NAME", "URL_SUSPICIOUSLY_LONG",
                     "URL_CDN_MISMATCH", "REDIRECT_EXCESSIVE_HOPS"})

EIGENE, HOCH, MITTLERE, VERDACHT, KEINE = 4, 3, 2, 1, 0


def stufe_aus_zeichen(gruende: list[str]) -> int:
    """Stufe allein aus den Zeichen der Erkennung (Gründe wie HEADER_SSAI_MARKER)."""
    zeichen = set(gruende)
    if zeichen & STARK:
        return HOCH
    if zeichen & MITTEL:
        return MITTLERE
    if len(zeichen & SCHWACH) >= 2:
        return VERDACHT
    return KEINE


def stufe(*, entscheidung: str | None, status: str | None, von_hand: bool, gruende: list[str],
          markiert: bool, widersprochen: bool) -> int:
    """Stufe eines Senders aus allem, was über ihn bekannt ist."""
    if entscheidung == "blocked" or status == "manual_blocked":
        return EIGENE
    if entscheidung == "allowed" or widersprochen:
        return KEINE
    if markiert or (von_hand and status == "confirmed_ad"):
        return HOCH
    return stufe_aus_zeichen(gruende)


def _gruende(reasons_json: str | None) -> list[str]:
    try:
        return [str(g.get("reason", "")) for g in json.loads(reasons_json or "[]") if isinstance(g, dict)]
    except (TypeError, ValueError):
        return []


def stufen_lesen(v: sqlite3.Connection, uuids: list[str] | None = None) -> dict[str, int]:
    """Stufe je Sender mit Erkennung oder eigener Bewertung (alle übrigen haben 0); mit `uuids` nur für diese."""
    bereich, werte = ("", []) if uuids is None else (" WHERE {} IN (SELECT value FROM json_each(?))", [json.dumps(uuids)])
    status = {z[0]: z for z in v.execute(
        "SELECT station_uuid, user_action, block_status, manually_set, reasons_json FROM station_ad_status"
        + bereich.format("station_uuid"), werte)}
    markiert, widersprochen = set(), set()
    for uuid, schluessel in v.execute(
            "SELECT station_uuid, tag_key FROM station_tags WHERE source = 'user' "
            "AND tag_key IN ('werbung', 'werbung_widerspruch')" + bereich.format("station_uuid").replace("WHERE", "AND"),
            werte):
        (markiert if schluessel == "werbung" else widersprochen).add(uuid)
    ergebnis = {}
    for uuid in set(status) | markiert | widersprochen:
        z = status.get(uuid)
        ergebnis[uuid] = stufe(entscheidung=z[1] if z else None, status=z[2] if z else None,
                               von_hand=bool(z[3]) if z else False, gruende=_gruende(z[4]) if z else [],
                               markiert=uuid in markiert, widersprochen=uuid in widersprochen)
    return ergebnis
