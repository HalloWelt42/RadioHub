"""
Filtersperren neu berechnen (RAD-2)

Bringt die Sperren mit category 'filter' auf den Stand der Ausschlüsse, mit exaktem Vergleich statt Wortteilen.
Es gelten die Sprachen der Einstellungen und die Tags früherer Ausblendungen (Entscheidung zu RAD-2, Variante C);
beim Anwenden landen diese Tags auch in den Einstellungen. Sperren von Hand und aus der Werbeerkennung bleiben
unberührt.

    python -m backend.werkzeuge.filtersperren_neu              Vorschau, ändert nichts
    python -m backend.werkzeuge.filtersperren_neu --anwenden   Sperren umschreiben

Im Betrieb im Container: docker exec radiohub-backend python -m backend.werkzeuge.filtersperren_neu
"""
from __future__ import annotations

import argparse
from collections import Counter

from ..database import db_session
from ..services import filtersperren

BEISPIELE = 15


def _gruende(sperren: list[filtersperren.Sperre]) -> list[tuple[str, int]]:
    zaehler = Counter(teil for s in sperren for teil in s.grund.split(", "))
    return zaehler.most_common(BEISPIELE)


def bericht(abgleich: filtersperren.Abgleich, kriterien: filtersperren.FilterKriterien, angewendet: bool) -> str:
    zeilen = [
        "Filtersperren " + ("umgeschrieben" if angewendet else "Vorschau (nichts geändert)"),
        f"Ausschlüsse: {len(kriterien.sprachen)} Sprachen, {len(kriterien.tags)} Tags, "
        f"Mindeststimmen {kriterien.mindeststimmen}",
        f"Wieder sichtbar:   {len(abgleich.frei)}",
        f"Neu ausgeblendet:  {len(abgleich.neu)}",
        f"Bleiben gesperrt:  {len(abgleich.bleiben)} (Grund wird auf den Treffer gekürzt)",
        f"Favoriten wieder sichtbar ({len(abgleich.favoriten_frei)}): " + ", ".join(abgleich.favoriten_frei),
        f"Favoriten neu ausgeblendet ({len(abgleich.favoriten_neu)}): " + ", ".join(abgleich.favoriten_neu),
        "Häufigste Gründe der verbleibenden und neuen Sperren:",
    ]
    zeilen += [f"  {anzahl:6d}  {grund}" for grund, anzahl in _gruende(abgleich.bleiben + abgleich.neu)]
    return "\n".join(zeilen)


def main() -> None:
    teiler = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    teiler.add_argument("--anwenden", action="store_true", help="Sperren wirklich umschreiben")
    argumente = teiler.parse_args()

    with db_session() as conn:
        kriterien = filtersperren.kriterien_fuer_neuberechnung(conn)
        if argumente.anwenden:
            abgleich = filtersperren.anwenden(conn, kriterien)
        else:
            abgleich = filtersperren.abgleichen(conn, kriterien)
    if argumente.anwenden:
        # erst nach dem Abschluss der Sperren: der Einstellungsdienst schreibt über eine eigene Verbindung
        filtersperren.in_einstellungen_uebernehmen(kriterien)
    print(bericht(abgleich, kriterien, argumente.anwenden))


if __name__ == "__main__":
    main()
