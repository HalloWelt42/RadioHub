# RAD-8: Funktionen der Abspielleiste, alt und neu

Vorgabe des Nutzers (17.11.2026): "Achte darauf, dass keine Funktionen verschwinden bei UI-Neugestaltung in der
Steuerung des Players." Liste aller Bedienfunktionen der alten Leiste (`components/HiFiPlayer.svelte`, Stand da227d2,
dazu die Tastatur in `App.svelte`) und wo sie in der Kanzel (`frontend/src/spieler/`) stehen. Was in einem Zustand
nicht gilt, ist wie bisher gesperrt und bleibt sichtbar; ausgeblendet ist nur die Zeile Zeitversatz außerhalb des
Zeitversatzes (Auftrag RAD-8: "Zeitversatz-Zeile nur, wenn Zeitversatz verfügbar ist"), deren Knöpfe in der alten
Leiste dort gesperrt waren.

Prüfung: `tests/kanzel.test.ts` (vitest, Zuordnung Zustand zu Anzeige und Tasten) und der Browserlauf
`frontend/tests/kanzel-browser.mjs ablauf` gegen den Probebetrieb (echte Wiedergabe, unsichtbarer Chrome ohne Ton).
Die Kennung (F01 ...) ist die des Browserlaufs; alle 39 Prüfungen bestanden (17.11.2026).

| Nr | Alt (HiFiPlayer) | Neu (Kanzel) | Prüfung | Stand |
|---|---|---|---|---|
| F01 | Laufschrift DISPLAY: Titel oder Sendername, lief per Breitenmessung | Punktmatrix mit dem Sender (Stellen aus der Breite, Lauf über ihr Merkmal), Titelzeile nur mit Titel | F01, vitest Anzeige | erledigt |
| F02 | QUELLE: Tuner, Podcast, Aufnahme, Cutter, Datei und Modus (HLS, LIVE, STREAM, REC) | Quelle in 14 Segmenten (DIREKT, LIVE, VERSATZ, PODCAST, ARCHIV, SCHNITT, DATEI, REC, LÄDT, PAUSE, FEHLER), Statuszeile mit Art und Format | F02, F02b, vitest | erledigt |
| F03 | Zwei VU-Leuchtketten, aktiv beim Spielen (nachgestellt) | Zwei Pegel des Appkerns neben dem Regler; nachgestelltes Signal beim Spielen, unten ohne Ton | F03, F03b | erledigt |
| F04 | Lautstärkeknopf (Ziehen) | Drehregler des Appkerns: Ziehen, Mausrad, Pfeiltasten, Doppelklick auf 50, Wert eintippen; gemerkt | F04 | erledigt |
| F05 | Lautstärke über Pfeil hoch und runter, M stumm (App) | unverändert in App.svelte; der Regler folgt | F05 | erledigt |
| F06 | ZEIT: Aufnahmedauer (rot), Position (grün), Abstand zu live (gelb), sonst 00:00:00 | Zeit in 7 Segmenten: Aufnahmedauer, Position, Abstand zu live mit Minus, sonst Hördauer des Senders; Farbe der Lage in Quelle und Leuchte | F06, F15, vitest | erledigt |
| F07 | Bitrate und Zahl erkannter Titel unter der Zeit während der Aufnahme | Statuszeile: AUFNAHME mit Dauer, Bitrate, erkannte Titel | F07, vitest | erledigt |
| F08 | Zeiten über dem Fader: Position und Dauer, LIVE oder Abstand, Puffer in Blau | Zeile unter der Zeit: "Position von Dauer" bzw. "Puffer von höchstens"; Abstand in Zeit und Statuszeile | F08, vitest | erledigt |
| F09 | Klick auf das Etikett der Steuerung: zur Quelle (bei Aufnahme zum Sender) | Klick auf die Punktmatrix: zum Sender, Podcast oder zur Aufnahme; Hinweis "Zum aufnehmenden Sender springen" während der Aufnahme | F09, F09b, F09c | erledigt (Podcast im Zeitversatz springt jetzt zum Podcast statt zum Radio) |
| F10 | Fader: spulen bei Podcast, Zeitversatz und Aufnahme; gesperrt bei Aufnahme; pulsiert beim Suchen | Spulbahn über dem Balken (Zeitversatz: über den Puffer, je Segment; Folge und Aufnahme: Position), Pfeiltasten, gesperrt bei Aufnahme, pulsiert beim Suchen | F10, F10b, vitest | erledigt |
| F11 | Zurück: Name des vorigen Senders, der vorigen Folge oder Aufnahme im Hinweis, leuchtet beim Drücken, gesperrt bei Aufnahme | Taste Zurück: gleicher Hinweis mit (Pfeil links), Tastenlicht beim Drücken, während der Aufnahme gesperrt mit Licht | F11, F11b, vitest | erledigt |
| F12 | 10 s zurück (Podcast, Zeitversatz, Aufnahme) | Folge und Aufnahme: 10 s zurück; Zeitversatz: 30 s zurück (Entwurf) | F12, F12b | erledigt |
| F13 | Stopp (S): beendet Hören und Aufnahme, leuchtet beim Drücken | Taste Stopp: gleich; gesperrt, wenn nichts läuft | F13 | erledigt |
| F14 | Spielen und Anhalten (Leertaste); Originalstrom nur beenden; Leuchte grün und gelb | Taste Spielen: Symbol Pause, Stopp im Originalstrom, Spielen; Kappe blau beim Spielen, Licht atmet in der Pause; gesperrt bei Aufnahme | F14, F14b, vitest | erledigt |
| F15 | Aufnahme: nur bei spielendem Sender, nicht bei Wiedergabe einer Aufnahme; rot blinkend; Stopp nur über Stopp | Taste Aufnahme: gleiche Regeln, Kappe rot, Licht blinkt; Anzeige rot blinkend, "Wechsel gesperrt" | F15, vitest | erledigt |
| F16 | 10 s vor | Folge und Aufnahme: 10 s vor; Zeitversatz: 30 s vor (gesperrt live) | F16, F16b | erledigt |
| F17 | Weiter: Name im Hinweis, Symbol gespiegelt bei rückwärts | Taste Weiter: gleich | F17, F17b, F20 | erledigt |
| F18 | Live: nur im Zeitversatz, blaue Leuchte wenn zurück | Knopf Live in der Zeile Zeitversatz, gesperrt wenn live oder bei Aufnahme | F18 | erledigt |
| F19 | Original oder HLS umschalten, Taste bleibt gedrückt bis zum Wechsel, Leuchte grün oder gelb | Taste Original oder Zeitversatz: immer da, gesperrt wo kein Wechsel geht; Licht grün oder gelb, atmet bis zum Wechsel (höchstens 20 s) | F19, vitest | erledigt |
| F20 | Wiedergabemodus linear, rückwärts, Schleife, Zufall mit Leuchtfarbe | Taste Reihenfolge: immer da, gesperrt außer bei Folgen und Aufnahmen; Symbol und Lichtfarbe je Modus | F20, vitest | erledigt |
| F21 | HLS-Bitrate: acht Leuchten (erkannt grün, Vorgabe gelb), Klick setzt oder löscht die Vorgabe, gemerkt; gesperrt ohne Zeitversatz, bei Aufnahme, bei Podcast fest 128; "wechselt" | Statuszeile: Format mit erkannter Bitrate, daneben Auswahl der Bitrate (Wie gesendet, 32 bis 320); gemerkt unter demselben Schlüssel; Zeitversatz startet neu; gesperrt sichtbar im Originalstrom, fest 128 bei Podcast im Puffer, "wechselt ..." | F21, F21a | erledigt (Leuchten als Auswahl) |
| F22 | Klang beim Zeigen und Drücken | gleich (Senderwechsel ohne Klang wie bisher) | Code | erledigt |
| F23 | Titelabfrage alle 15 s bei Sendern mit Titelangabe | Tonausgang, gleich | F23 | erledigt |
| F24 | Laufende Aufnahme beim Start wiederherstellen | Tonausgang, gleich | F24 | erledigt |
| F25 | Audio-Element in der Leiste (Schnittansicht nutzt document.querySelector("audio")) | ein Audio-Element im Tonausgang der Kanzel | F25 | erledigt |
| F26 | Engine an das Element binden, Lautstärke angleichen | Tonausgang, gleich | F26 | erledigt |
| F27 | Leuchten der Tasten (Spielen, Stopp, Aufnahme, Modus) | Tastenlicht in der Kappe, Kappe leuchtet im Zustand | F27, F15 | erledigt |
| F28 | Tastatur: Leertaste, S, Pfeile, M, 1 bis 4 (App.svelte) | unverändert | F28, F05 | erledigt |
| F29 | Fehler nur als Meldung | Meldung wie bisher, dazu Zustand Fehler (rot, Art des Fehlers) mit "Neu verbinden" | F29, vitest | erledigt (neu) |
| F30 | Kontext-Etikett: Aufnahme, Wiedergabe, Podcast, Zeitversatz, Steuerung | Statuszeile: BEREIT, VERBINDET, PUFFERT, LIVE, HINTER LIVE, PAUSE, PODCAST, WIEDERGABE, AUFNAHME, Fehler | vitest | erledigt |

Nicht übernommen, weil ohne Funktion: der Platzhalter `lib/audioAnalyser.js` (tat nichts) und die nur von der alten
Leiste genutzten Bausteine `HiFiVuMeter` und `HiFiBitrateLed`.
