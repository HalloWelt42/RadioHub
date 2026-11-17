"""Überführung der heutigen Sperren in lebende Regeln (Entscheidung 5). Ziel: dieselben Sender bleiben sichtbar wie
heute; was sich ändert, steht mit Grund in der Vorschau.

Heute sichtbar ist (wie in der heutigen Oberfläche): nicht in der Sperrliste blocklist und nicht von den Ausschlüssen
der Filter-Einstellungen getroffen (Sprachen und Tags als ganze Einträge, Mindeststimmen). Daraus wird:

    Sprachen (filter_excluded_languages)   je Sprache eine Regel auf genau diese Einträge (Einträge ohne bekannte Sprache
                                           zusammen in einer Regel), nie auf den Code, damit "deu" nicht ganz Deutsch trifft
    Tags (Einstellung und Gründe der       eine Tag-Regel
      Filtersperren "tag:x")
    Mindeststimmen (Einstellung und        eine Regel
      Gründe "votes<n")
    Sperren von Hand                        Einzelsperren
    Werbesperren                            Werbeentscheidung "sperren" und eine Werbe-Regel ab Stufe "eigene"

Die Regel "altbestand" (die Sperrliste bis zur Überführung) fällt danach weg; die Tabelle blocklist bleibt unverändert
stehen. Eine Filtersperre, die keine Regel mehr erklärt (Wortteil-Vergleich vor RAD-2), wird sichtbar; ein Favorit
bleibt immer sichtbar (als Ausnahme)."""
from __future__ import annotations

import json
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from ...senderdaten import sprachen as sprachtabelle
from . import regeln, sichtbarkeit
from .modelle import SpracheEntwurf, StimmenEntwurf, TagEntwurf, WerbungEntwurf

UEBERFUEHRT = "regeln_ueberfuehrt"     # in cache_meta: Zeitpunkt der Überführung


def _eintraege(feld: str | None) -> set[str]:
    """Einträge wie im früheren Vergleich: an Kommas geteilt, ohne Rand, klein."""
    return {t for t in (roh.strip().lower() for roh in (feld or "").split(",")) if t}


def _config(v: sqlite3.Connection, schluessel: str, vorgabe: object) -> object:
    zeile = v.execute("SELECT value FROM config WHERE key = ?", (schluessel,)).fetchone()
    if not zeile:
        return vorgabe
    try:
        return json.loads(zeile[0])
    except (TypeError, ValueError):
        return vorgabe


@dataclass
class Plan:
    sprachgruppen: dict[str, list[str]] = field(default_factory=dict)   # Name der Gruppe -> Einträge
    tags: list[str] = field(default_factory=list)
    mindeststimmen: int = 0
    einzelsperren: list[tuple[str, str]] = field(default_factory=list)  # (uuid, name)
    werbesperren: list[str] = field(default_factory=list)


@dataclass
class Bericht:
    angewendet: bool
    plan: Plan
    regeln: list[tuple[str, int, int]]                 # (Titel, betroffen, davon Favoriten)
    gesamt: int
    vorher_sichtbar: int
    nachher_sichtbar: int
    neu_sichtbar: Counter                              # Grund -> Anzahl
    neu_ausgeblendet: Counter
    beispiele_sichtbar: dict[str, list[str]]
    beispiele_ausgeblendet: dict[str, list[str]]
    favoriten_neu_sichtbar: list[str]
    favoriten_neu_ausgeblendet: list[str]


def plan_lesen(v: sqlite3.Connection) -> Plan:
    plan = Plan()
    sprachen = sorted({str(s).strip().lower() for s in (_config(v, "filter_excluded_languages", []) or []) if str(s).strip()})
    gruppen: dict[str, list[str]] = defaultdict(list)
    for eintrag in sprachen:
        code = sprachtabelle.code_von(eintrag)
        gruppen[sprachtabelle.name_von(code) if code else ""].append(eintrag)
    plan.sprachgruppen = dict(sorted(gruppen.items()))
    tags = {str(t).strip().lower() for t in (_config(v, "filter_excluded_tags", []) or []) if str(t).strip()}
    stimmen = int(_config(v, "filter_min_votes", 0) or 0)
    for (grund,) in v.execute("SELECT DISTINCT reason FROM blocklist WHERE category = 'filter'"):
        for teil in (grund or "").split(", "):
            if teil.startswith("tag:") and teil[4:]:
                tags.add(teil[4:].strip().lower())
            elif teil.startswith("votes<") and teil[6:].isdigit():
                stimmen = max(stimmen, int(teil[6:]))
    plan.tags = sorted(tags)
    plan.mindeststimmen = stimmen
    plan.einzelsperren = [(z[0], z[1] or "") for z in v.execute(
        "SELECT uuid, name FROM blocklist WHERE category IS NULL OR category NOT IN ('filter', 'ad') ORDER BY uuid")]
    plan.werbesperren = [z[0] for z in v.execute("SELECT uuid FROM blocklist WHERE category = 'ad' ORDER BY uuid")]
    return plan


def heute_sichtbar(v: sqlite3.Connection) -> set[str]:
    """Sichtbar in der heutigen Oberfläche (ohne Verschwundene, die es dort nicht gab)."""
    gesperrt = {z[0] for z in v.execute("SELECT uuid FROM blocklist")}
    sprachen = {str(s).strip().lower() for s in (_config(v, "filter_excluded_languages", []) or [])}
    tags = {str(t).strip().lower() for t in (_config(v, "filter_excluded_tags", []) or [])}
    stimmen = int(_config(v, "filter_min_votes", 0) or 0)
    return {z["uuid"] for z in v.execute("SELECT uuid, language, tags, votes FROM stations WHERE verschwunden_am IS NULL")
            if z["uuid"] not in gesperrt and not (_eintraege(z["language"]) & sprachen)
            and not (_eintraege(z["tags"]) & tags) and (z["votes"] or 0) >= stimmen}


def anwenden(v: sqlite3.Connection, plan: Plan, zeit: str) -> None:
    """Legt Regeln, Einzelsperren und Werbeentscheidungen an und nimmt die Regel "altbestand" weg (in der
    Transaktion des Aufrufers); danach ist die Sichtbarkeit neu berechnet."""
    for name, eintraege in plan.sprachgruppen.items():
        regeln.anlegen(v, SpracheEntwurf(eintraege=eintraege), zeit, "ueberfuehrt")
    if plan.tags:
        regeln.anlegen(v, TagEntwurf(tags=plan.tags), zeit, "ueberfuehrt")
    if plan.mindeststimmen > 0:
        regeln.anlegen(v, StimmenEntwurf(mindeststimmen=plan.mindeststimmen), zeit, "ueberfuehrt")
    v.executemany("INSERT OR IGNORE INTO sender_sperre (uuid, name, herkunft, angelegt_am) VALUES (?, ?, 'ueberfuehrt', ?)",
                  [(u, n, zeit) for u, n in plan.einzelsperren])
    if plan.werbesperren:
        v.executemany("""INSERT INTO station_ad_status (station_uuid, block_status, user_action, blocked_at)
                         VALUES (?, 'manual_blocked', 'blocked', ?)
                         ON CONFLICT(station_uuid) DO UPDATE SET user_action = 'blocked'
                         WHERE station_ad_status.user_action IS NOT 'blocked'
                           AND station_ad_status.block_status IS NOT 'manual_blocked'""",
                      [(u, zeit) for u in plan.werbesperren])
        if not regeln.gleiche(v, WerbungEntwurf(stufe="eigene")):
            regeln.anlegen(v, WerbungEntwurf(stufe="eigene"), zeit, "ueberfuehrt")
    regeln.entfernen(v, regeln.ALTBESTAND)
    v.execute("INSERT OR REPLACE INTO cache_meta (key, value) VALUES (?, ?)", (UEBERFUEHRT, zeit))
    sichtbarkeit.neu_berechnen(v)


def _grund_sichtbar(v: sqlite3.Connection, uuid: str, favoriten: set[str]) -> str:
    zeile = v.execute("SELECT category, reason FROM blocklist WHERE uuid = ?", (uuid,)).fetchone()
    if uuid in favoriten:
        art = {"ad": "Werbesperre", "filter": "Filtersperre"}.get(zeile[0] if zeile else "", "Sperre von Hand")
        return f"Favorit trotz {art}, bleibt als Ausnahme sichtbar"
    if zeile and zeile[0] == "filter":
        return "Filtersperre, die keine Regel mehr trifft (früherer Vergleich mit Wortteilen)"
    if zeile:
        return f"Sperre der Art {zeile[0] or 'manual'} ohne Gegenstück"
    return "sonst"


def vergleichen(v: sqlite3.Connection, plan: Plan, vorher: set[str], angewendet: bool) -> Bericht:
    favoriten = {z[0]: z[1] or "" for z in v.execute("SELECT uuid, name FROM favorites")}
    nachher = {z[0] for z in v.execute("SELECT uuid FROM sender_index WHERE sichtbar = 1 AND verschwunden = 0")}
    namen = dict(v.execute("SELECT uuid, name FROM stations").fetchall())
    neu_sichtbar, neu_aus = Counter(), Counter()
    beispiele_s: dict[str, list[str]] = defaultdict(list)
    beispiele_a: dict[str, list[str]] = defaultdict(list)
    for uuid in sorted(nachher - vorher):
        grund = _grund_sichtbar(v, uuid, set(favoriten))
        neu_sichtbar[grund] += 1
        if len(beispiele_s[grund]) < 8:
            beispiele_s[grund].append(namen.get(uuid) or uuid)
    nrs = {z[0]: z[1] for z in v.execute("SELECT uuid, nr FROM sender_index")}
    weg = sorted(vorher - nachher)
    gruende = sichtbarkeit.gruende(v, [nrs[u] for u in weg if u in nrs])
    for uuid in weg:
        liste = gruende.get(nrs.get(uuid, -1), [])
        grund = liste[0].titel if liste else "ohne Regel"
        neu_aus[grund] += 1
        if len(beispiele_a[grund]) < 8:
            beispiele_a[grund].append(namen.get(uuid) or uuid)
    uebersicht = [(r.titel, r.betroffen, r.favoriten) for r in regeln.alle(v)]
    return Bericht(
        angewendet=angewendet, plan=plan, regeln=uebersicht,
        gesamt=v.execute("SELECT COUNT(*) FROM sender_index WHERE verschwunden = 0").fetchone()[0],
        vorher_sichtbar=len(vorher), nachher_sichtbar=len(nachher), neu_sichtbar=neu_sichtbar, neu_ausgeblendet=neu_aus,
        beispiele_sichtbar=dict(beispiele_s), beispiele_ausgeblendet=dict(beispiele_a),
        favoriten_neu_sichtbar=sorted(favoriten[u] for u in nachher - vorher if u in favoriten),
        favoriten_neu_ausgeblendet=sorted(favoriten[u] for u in vorher - nachher if u in favoriten))


def schon_ueberfuehrt(v: sqlite3.Connection) -> str | None:
    zeile = v.execute("SELECT value FROM cache_meta WHERE key = ?", (UEBERFUEHRT,)).fetchone()
    return zeile[0] if zeile else None
