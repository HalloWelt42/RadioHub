"""Senderquelle des Backends (RAD-7, Entscheidungen 4 bis 6, 18, 19): Abfrage mit Facetten, lebende Ausschlussregeln,
Sichtbarkeit mit Grund je Sender, ausgeblendete Sender, Einzelsperren und Freigaben, Abgleich mit dem
Senderverzeichnis. Die Schnittstelle (routers/radio.py) ruft nur die Funktionen dieses Pakets; SQL steht allein hier.

    Datenschicht   bestand, regeln, sichtbarkeit, abfrage, ausgeblendet, werbung (Funktionen auf einer Verbindung)
    Dienst         dienst (asynchron, über die Datenbank des Appkerns: lesen im Vorrat, schreiben in einer Transaktion)
    Auftrag        abgleich (nächtlich und auf Anstoß, mit Fortschritt)
"""
