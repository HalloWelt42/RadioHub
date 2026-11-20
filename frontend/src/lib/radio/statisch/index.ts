// Statische Senderquelle der Webversion (RAD-4): Liste aus sender.json, eigene Angaben im Speicher des Browsers.
export { StatischeQuelle, SPEICHER_SCHLUESSEL, type StatischeOptionen } from "./statische-quelle";
export { browserSpeicher, fluechtigerSpeicher, type Speicher } from "./speicher";
export { NichtVerfuegbar, NichtGefunden, Quellfehler } from "./fehler";
export { Formatfehler, FORMAT, SPALTEN } from "./format";
