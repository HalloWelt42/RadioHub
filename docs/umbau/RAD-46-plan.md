# RAD-46: Puffer und Aufnahme zusammen

Geklärt mit dem Nutzer am 22.11.2026 (Frage für Frage). Wortlaut des Auftrags am Ticket RAD-46, Fehlerbehebungen
vorab in RAD-47 (Vorlauf als Werbung) und RAD-48 (Puffer-Aufnahme behält Titel und Werbung, gleicher Feinschnitt).

## Grundgedanke

Der Puffer ist schon eine begonnene Aufnahme mit eigenem Verhalten. Beide hängen an derselben Verbindung zum Sender
mit denselben Sendedaten (Titelbuch, Werbestellen, Stillen, Pegel) und derselben Zeitachse (Sekunden des Tons, Stück N
des Puffers beginnt bei N Sekunden). Eine Aufnahme ist ein Abschnitt dieser Zeitachse, der Feinschnitt derselbe wie bei
einer Aufnahme vom Sender.

## Entscheidungen

1. Beginn einer Aufnahme bei laufendem Puffer: "Anfang des laufenden Titels". Sie beginnt an der Pause vor dem Titel,
   der gerade läuft (Regel des Feinschnitts); läuft Werbung, am Anfang des Titels nach der Werbung.
2. Radio aus oder Senderwechsel während einer Aufnahme aus dem Puffer: "Weiterlaufen bis Stopp". Die Aufnahme
   übernimmt nahtlos die Verbindung zum Sender und läuft weiter, bis sie beendet wird; ein Senderwechsel startet einen
   neuen Puffer für den neuen Sender.
3. Marken im Balken des Zeitversatzes: "Titelgrenzen und Werbung". Feiner Strich an jeder Titelgrenze (an der Pause),
   Werbung als Bernstein-Fläche, Titel beim Überfahren oder Antippen; während einer Aufnahme ihr Bereich rot hinterlegt.
4. Großansicht: "Liste mit Zeitleiste". Eigene Ansicht über der Radioansicht: oben eine breite Zeitleiste des ganzen
   Puffers mit Marken und Zoom, darunter die Titel als Liste (Zeit, Titel, Länge, Werbung markiert).
5. Aktionen in der Großansicht: hinspringen und hören; Aufnahme ab hier (ab Anfang dieses Titels, läuft bis Stopp);
   Bereich als Aufnahme sichern (von Titel A bis Titel B, auch ein einzelner Titel, fertig geschnitten); vorheriger und
   nächster Titel sowie über Werbung springen, auch im kleinen Balken.
6. Telefon: "Ja, als Liste". Titelliste des Puffers mit Springen, Aufnahme ab hier und Bereich sichern; die Zeitleiste
   schmal oben, ohne Zoom.
7. Pegel im Puffer: "Ja, mitmessen" (EBU R128, alle 100 ms), damit Aufnahmen und Bereiche aus dem Puffer so genau
   geschnitten werden wie Aufnahmen vom Sender. Die Last auf dem Pi wird vorher gemessen und gemeldet.
8. Einstellung "Rückblick der Puffer-Aufnahme": "Entfernen". Weiter zurück geht über "Aufnahme ab hier".
9. Öffnen der Großansicht: "Knopf am Balken" mit eigener Adresse (etwa `/radio/puffer`); am Telefon derselbe Knopf im
   Spieler.

## Technische Folgen (ohne Rückfrage, aus den Entscheidungen)

- Eine Schicht "Empfang" je Sender: Stromleser, Titelbuch, Werbestellen, Stillenwächter mit Pegel. Abnehmer sind der
  Puffer (HLS) und die Aufnahme; endet der Puffer, bleibt der Empfang, solange eine Aufnahme ihn braucht. Die
  Puffer-Aufnahme hängt dann nicht mehr an Kopien der Stücke, sondern ist ein Abschnitt des Empfangs.
- Titelgrenzen für Balken und Liste rechnet der Server mit der Regel des Feinschnitts (eine Wahrheit, keine zweite
  Rechnung in der Oberfläche); die Oberfläche bekommt Abschnitte (von, bis, Titel, Art).
- Die Dauer einer laufenden Aufnahme zählt ab ihrem Beginn im Ton, nicht ab dem Klick (heute zeigt die Uhr 0:00,
  obwohl schon 15 min Rückblick darin sind).

## Reihenfolge des Baus

1. Empfang als eigene Schicht; Aufnahme läuft weiter, wenn der Puffer endet; Pegel im Puffer mit Messung der Last.
2. Beginn am laufenden Titel; "Bereich sichern" und "Aufnahme ab hier" als Schnittstelle; Abschnitte des Puffers als
   Schnittstelle; Einstellung Rückblick entfernen (Übergang der gespeicherten Einstellung).
3. Entwurf für Balken mit Marken und Großansicht (Rechner und Telefon) zur Abnahme durch den Nutzer.
4. Oberfläche nach dem abgenommenen Entwurf, Handbuch, Prüfung im Betrieb.

## Später

- Vorlauf bei erneuter Verbindung mitten in einer langen Aufnahme (heute gilt die Erkennung nur für die erste Angabe).
