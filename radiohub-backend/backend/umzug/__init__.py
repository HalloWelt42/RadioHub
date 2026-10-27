"""Umzug des Altbestands in die Ablage (Kellerwolke) und in die Datenbank des RadioHub.

Quellen:
- das heutige RadioHub: Podcast-Folgen und Aufnahmen unter `<DATA_PATH>/recordings` mit lokalen Pfaden in der
  Datenbank; danach stehen dort die Pfade der Ablage
- das alte Radio (`--altes-radio`, Ordner mit pyradio.db und recordings/): Favoriten, Abos, Folgen und gemerkte
  Folgen in die Datenbank (ohne Doppel), Dateien in die Ablage

Wiederaufnehmbar: jede Datei steht mit Ziel und Prüfsumme in `umzug_dateien`; ein zweiter Lauf macht nur den Rest.
Die Quellen bleiben unangetastet; erst `--aufraeumen` verschiebt die Quellordner (nie löschen) in einen Papierkorb.

    python -m backend.umzug [--altes-radio PFAD] [--probe | --aufraeumen --papierkorb PFAD]
"""
