// Zuordnung Zustand -> Anzeige der Kanzel (Abspielleiste am Rechner, Entwurf mockups/radio-filter/rechner.html, RAD-8).
// Eine Stelle, die aus dem Zustand der Wiedergabe (appState und was der Tonausgang meldet) ableitet, was die Module
// zeigen: Statuszeile, Punktmatrix, Titelzeile, Quelle, Zeit, welche Zeile unter der Zeit steht und wie die Tasten der
// Steuerung leuchten, gesperrt sind und heißen. Ohne Svelte und ohne Seiteneffekte, darum mit vitest prüfbar
// (tests/kanzel.test.ts); die Bausteine setzen das Ergebnis nur ein.
import type { Leuchtfarbe } from "appkern-oberflaeche/instrumente";
import { formatTime, formatTimeShort } from "../lib/formatters.js";

export type Uebersetzer = (schluessel: string, werte?: Record<string, string | number>) => string;

/** Was das Audio-Element meldet: Laden, Puffern, Spielen oder Fehler (Code des MediaError) */
export type Medium = "ruhe" | "laedt" | "puffert" | "spielt" | "fehler";

/** Zustände der Kanzel, wie im Entwurf (ohne "fern" und "web": Übergabe kommt mit Etappe 4) */
export type Zustand = "leer" | "laedt" | "puffert" | "live" | "versatz" | "pause" | "podcast" | "wiedergabe" | "aufnahme" | "fehler";

export type Leuchtzustand = "an" | "aus" | "blinkt" | "atmet";

interface Sender { uuid?: string; name?: string; codec?: string; bitrate?: number }
interface Folge { title?: string; duration?: number; podcast?: { title?: string } | null }
interface Aufnahme { name?: string; station_name?: string; source?: string; path?: string }
export interface HlsStand {
  first_segment?: number | null;
  last_segment?: number | null;
  segment_duration?: number;
  buffered_seconds?: number;
  max_segments?: number;
}

/** Ausschnitt aus appState und dem Tonausgang, den die Kanzel liest */
export interface Stand {
  isPlaying: boolean;
  isPaused: boolean;
  isRecording: boolean;
  playerMode: string;
  isLive: boolean;
  currentStation: Sender | null;
  currentEpisode: Folge | null;
  currentRecording: Aufnahme | null;
  streamTitle: string | null;
  streamQuality: { inputCodec?: string; inputBitrate?: number; outputBitrate?: number } | null;
  hlsStatus: HlsStand | null;
  hlsActive: boolean;
  currentSegment: number | null;
  recordingElapsed: number;
  recordingIcyCount: number;
  canPlayDirect: boolean;
  canPlayHLS: boolean | null;
  playMode: string;
  stations: Sender[];
  podcastPlaylist: Folge[];
  currentEpisodeIndex: number;
  recordingPlaylist: Aufnahme[];
  medium: Medium;
  fehlerCode: number | null;
  zeit: number;
  dauer: number;
  /** Lage auf der Spulbahn, 0 bis 100 (Engine) */
  lage: number;
  hoerdauer: number;
  /** was der Weg der Wiedergabe kann (wiedergabeweg.js); ohne Angabe alles wie in der vollen App */
  weg?: { zeitversatz: boolean; aufnahme: boolean };
}

/** Woher der Ton kommt, unabhängig davon, ob er gerade läuft */
export type Art = "keine" | "sender" | "podcast" | "aufnahme";

export function artVon(s: Stand): Art {
  if (s.currentEpisode) return "podcast";
  if (s.currentRecording) return "aufnahme";
  if (s.currentStation) return "sender";
  return "keine";
}

/** Sekunden hinter der Live-Kante im Zeitversatz (HLS): Segmente bis zum letzten mal ihre Länge */
export function sekundenHinterLive(hls: HlsStand | null, segment: number | null): number {
  if (hls?.last_segment == null || segment == null) return 0;
  return Math.max(0, (hls.last_segment - segment) * (hls.segment_duration || 1));
}

/** Zeitversatz des Senders (HLS, keine Folge): nur dann stehen 30 s zurück, Puffer und Live */
export const hatZeitversatz = (s: Stand): boolean => s.playerMode === "hls" && !!s.currentStation && !s.currentEpisode;

/** Spulen über die Position: Folgen und Aufnahmen */
export const hatPosition = (s: Stand): boolean => artVon(s) === "podcast" || artVon(s) === "aufnahme";

export function zustandVon(s: Stand): Zustand {
  const art = artVon(s);
  if (s.isRecording) return "aufnahme";
  if (art === "keine" || (!s.isPlaying && !s.isPaused)) return "leer";
  if (s.medium === "fehler") return "fehler";
  if (s.isPaused) return "pause";
  if (s.medium === "laedt") return "laedt";
  if (s.medium === "puffert") return "puffert";
  if (art === "podcast") return "podcast";
  if (art === "aufnahme") return "wiedergabe";
  if (hatZeitversatz(s) && !s.isLive) return "versatz";
  return "live";
}

const QUELLFARBE: Record<Zustand, Leuchtfarbe> = {
  leer: "blau", laedt: "gelb", puffert: "gelb", live: "blau", versatz: "bernstein", pause: "gelb", podcast: "gruen",
  wiedergabe: "gruen", aufnahme: "rot", fehler: "rot",
};

export interface Anzeige {
  zustand: Zustand;
  /** Statuszeile: was gerade geschieht */
  art: string;
  /** Statuszeile: Codec und Bitrate, bei Aufnahme Bitrate und erkannte Titel */
  format: string | null;
  /** Punktmatrix: Sender, Podcast oder aufgenommener Sender (die Matrix schreibt in Versalien) */
  sender: string;
  /** Titelzeile, nur mit Titel */
  titel: string | null;
  quelle: { text: string; farbe: Leuchtfarbe };
  zeit: string;
  /** Anzeige rot getönt */
  ton: "fehler" | "";
  /** Zeile unter Quelle und Zeit: Zeitversatz (Sender im HLS), Position (Folge, Aufnahme) oder keine */
  zeile: "zeitversatz" | "position" | null;
}

function quelltext(z: Zustand, s: Stand, t: Uebersetzer): string {
  switch (z) {
    case "leer": return "";
    case "live": return t(s.playerMode === "direct" ? "kanzel.quelle_direkt" : "kanzel.quelle_live");
    case "wiedergabe": {
      const herkunft = s.currentRecording?.source;
      return t(herkunft === "cutter" ? "kanzel.quelle_schnitt" : herkunft === "file" ? "kanzel.quelle_datei"
        : herkunft === "podcast" ? "kanzel.quelle_podcast" : "kanzel.quelle_archiv");
    }
    default: return t(`kanzel.quelle_${z}`);
  }
}

function artText(z: Zustand, s: Stand, t: Uebersetzer): string {
  switch (z) {
    // "Originalstrom" nur, wo es auch einen Zeitversatz gibt (nicht in der Webversion)
    case "live": return t(s.playerMode === "direct" && s.weg?.zeitversatz !== false ? "kanzel.art_direkt" : "kanzel.art_live");
    case "versatz": return t("kanzel.art_versatz", { zeit: formatTimeShort(sekundenHinterLive(s.hlsStatus, s.currentSegment)) });
    case "aufnahme": return t("kanzel.art_aufnahme", { zeit: formatTime(s.recordingElapsed) });
    case "fehler": return t(s.fehlerCode === 2 ? "kanzel.art_fehler_netz" : s.fehlerCode === 3 ? "kanzel.art_fehler_format" : "kanzel.art_fehler");
    default: return t(`kanzel.art_${z}`);
  }
}

function formatText(z: Zustand, s: Stand, t: Uebersetzer): string | null {
  const q = s.streamQuality;
  if (z === "aufnahme") {
    const br = q?.outputBitrate || q?.inputBitrate;
    if (!br) return null;
    const bitrate = t("kanzel.kbit", { n: br });
    return s.recordingIcyCount > 0 ? `${bitrate} · ${t("kanzel.titelZahl", { n: s.recordingIcyCount })}` : bitrate;
  }
  if (z === "leer") return null;
  const art = artVon(s);
  if (art === "podcast" && s.playerMode === "hls") return `AAC ${t("kanzel.kbit", { n: q?.outputBitrate || 128 })}`;
  if (art !== "sender") return null;
  const codec = q?.inputCodec || s.currentStation?.codec || "";
  const br = q?.inputBitrate || s.currentStation?.bitrate || 0;
  const teile = [codec.toUpperCase(), br > 0 ? t("kanzel.kbit", { n: br }) : ""].filter(Boolean);
  return teile.length ? teile.join(" ") : null;
}

function senderUndTitel(s: Stand): { sender: string; titel: string | null } {
  const folge = s.currentEpisode, aufnahme = s.currentRecording, station = s.currentStation;
  if (folge) {
    const podcast = folge.podcast?.title || "";
    return podcast ? { sender: podcast, titel: folge.title || null } : { sender: folge.title || "", titel: null };
  }
  if (aufnahme) {
    const sender = aufnahme.station_name || aufnahme.name || "";
    return { sender, titel: aufnahme.name && aufnahme.name !== sender ? aufnahme.name : null };
  }
  if (station) return { sender: station.name || "", titel: s.streamTitle || null };
  return { sender: "", titel: null };
}

function zeitText(z: Zustand, s: Stand): string {
  if (z === "aufnahme") return formatTime(s.recordingElapsed);
  if (z === "leer" || z === "laedt" || z === "fehler") return "--:--:--";
  if (z === "versatz") return `-${formatTime(sekundenHinterLive(s.hlsStatus, s.currentSegment))}`;
  return formatTime(hatPosition(s) ? s.zeit : s.hoerdauer);
}

export function kanzelAnzeige(s: Stand, t: Uebersetzer): Anzeige {
  const zustand = zustandVon(s);
  const aktiv = zustand !== "leer" || s.isRecording;
  const { sender, titel } = aktiv ? senderUndTitel(s) : { sender: "", titel: null };
  return {
    zustand,
    art: artText(zustand, s, t),
    format: formatText(zustand, s, t),
    sender,
    titel,
    quelle: { text: quelltext(zustand, s, t), farbe: QUELLFARBE[zustand] },
    zeit: zeitText(zustand, s),
    ton: zustand === "fehler" ? "fehler" : "",
    zeile: !aktiv ? null : hatZeitversatz(s) ? "zeitversatz" : hatPosition(s) ? "position" : null,
  };
}

// ═══ Steuerung ═══

export interface Taste {
  /** ganze Kappe leuchtet */
  an: boolean;
  /** Tastenlicht (Lichtschlitz in der Kappe) */
  licht: Leuchtzustand;
  gesperrt: boolean;
  hilfe: string;
}
export interface Tasten {
  zurueck: Taste;
  stopp: Taste;
  /** nach einem Fehler: Neu verbinden (lädt die Quelle von vorn) statt Spielen oder Anhalten */
  spielen: Taste & { symbol: string; neuVerbinden: boolean; farbe: Leuchtfarbe };
  aufnahme: Taste;
  vor: Taste & { gespiegelt: boolean };
  /** Original oder Zeitversatz; immer da, gesperrt außer bei Sendern mit möglichem Wechsel (wie in HiFiPlayer) */
  modus: Taste & { symbol: string; farbe: Leuchtfarbe };
  /** linear, rückwärts, Schleife, Zufall; immer da, gesperrt außer bei Folgen und Aufnahmen (wie in HiFiPlayer) */
  reihenfolge: Taste & { symbol: string; farbe: Leuchtfarbe };
  /** Fokus auf den laufenden Sender ein oder aus (RAD-19, Licht = ein); nach einem Fehler beim Sender: andere Variante */
  quelle: Taste & { varianten: boolean };
}

const REIHENFOLGE: Record<string, { symbol: string; farbe: Leuchtfarbe; text: string }> = {
  linear: { symbol: "fa-arrow-right", farbe: "weiss", text: "player.linear" },
  reverse: { symbol: "fa-arrow-left", farbe: "bernstein", text: "player.rueckwaerts" },
  loop: { symbol: "fa-repeat", farbe: "gruen", text: "player.endlosschleife" },
  shuffle: { symbol: "fa-shuffle", farbe: "gelb", text: "player.zufall" },
};
export const REIHENFOLGEN = ["linear", "reverse", "loop", "shuffle"] as const;

/** Name des Nachbarn in der Liste (Sender, Folge oder Aufnahme), rundum wie die Aktionen im Store */
export function nachbar(s: Stand, schritt: -1 | 1): string | null {
  if (s.currentEpisode && s.podcastPlaylist.length > 1) {
    const i = s.currentEpisodeIndex + schritt;
    return i >= 0 && i < s.podcastPlaylist.length ? (s.podcastPlaylist[i]?.title ?? null) : null;
  }
  if (s.playerMode === "recording" && s.recordingPlaylist.length > 1) {
    const i = s.recordingPlaylist.findIndex((x) => x.path === s.currentRecording?.path);
    if (i < 0) return null;
    const n = s.recordingPlaylist.length;
    return s.recordingPlaylist[(i + schritt + n) % n]?.name ?? null;
  }
  if (!s.currentStation || !s.stations.length) return null;
  const i = s.stations.findIndex((x) => x.uuid === s.currentStation?.uuid);
  if (i < 0) return null;
  const n = s.stations.length;
  return s.stations[(i + schritt + n) % n]?.name ?? null;
}

/** Senderwechsel und Blättern möglich (wie HiFiPlayer): Senderliste, Folge oder Aufnahmen mit mehr als einem Eintrag */
export const kannBlaettern = (s: Stand): boolean =>
  s.stations.length > 0 || !!s.currentEpisode || (s.playerMode === "recording" && s.recordingPlaylist.length > 1);

export const kannModusWechseln = (s: Stand): boolean =>
  !s.isRecording && !s.currentEpisode && ((s.playerMode === "hls" && s.canPlayDirect) || (s.playerMode === "direct" && s.canPlayHLS === true));

export function kanzelTasten(s: Stand, t: Uebersetzer, modusWechselt = false, fokusAn = false): Tasten {
  const art = artVon(s), rec = s.isRecording, laeuft = s.isPlaying && !s.isPaused;
  const folge = art === "podcast", aufnahme = s.playerMode === "recording";
  const blaettern = kannBlaettern(s);
  const mitTaste = (text: string, taste: string) => t("kanzel.taste", { text, taste });

  const blatt = (schritt: -1 | 1): Taste => {
    const richtung = schritt < 0 ? "prev" : "next";
    let hilfe: string;
    if (rec) hilfe = t("kanzel.wechselGesperrtHilfe");
    else if (!blaettern) hilfe = t(folge ? `player.keine${schritt < 0 ? "Prev" : "Next"}Episode` : aufnahme ? `player.keine${schritt < 0 ? "Prev" : "Next"}Titel` : `player.kein${schritt < 0 ? "Prev" : "Next"}`);
    else hilfe = mitTaste(nachbar(s, schritt) || t(folge ? `player.${richtung}Episode` : aufnahme ? `player.${richtung}Titel` : `player.${richtung}Sender`), schritt < 0 ? "←" : "→");
    return { an: false, licht: rec ? "an" : "aus", gesperrt: rec || !blaettern, hilfe };
  };

  const quelleDa = art !== "keine";
  const fehler = zustandVon(s) === "fehler";
  const spielen: Tasten["spielen"] = fehler
    ? { an: false, licht: "atmet", farbe: "rot", gesperrt: false, symbol: "fa-play", neuVerbinden: true, hilfe: t("kanzel.neuVerbindenHilfe") }
    : {
      // bleibt Spielen (Symbol und Weg, aktionen.spielenOderPause): das Licht zeigt, ob es spielt (an), lädt (blinkt)
      // oder pausiert (atmet); beendet wird nur über Stopp (Nutzer 20.11.2026)
      an: laeuft,
      licht: rec || (laeuft && zustandVon(s) !== "laedt") ? "an" : laeuft ? "blinkt" : s.isPaused ? "atmet" : "aus",
      farbe: "blau",
      gesperrt: rec || !quelleDa,
      symbol: "fa-play",
      neuVerbinden: false,
      hilfe: rec ? t("player.recLaeuft")
        : mitTaste(laeuft ? t("player.pause") : s.isPaused ? t(s.playerMode === "direct" ? "kanzel.weiterLive" : "kanzel.weiter") : t("player.play"), t("kanzel.leertaste")),
    };

  const aufnahmeMoeglich = art === "sender" && s.isPlaying && !aufnahme;
  const aufnehmen: Taste = {
    an: rec, licht: rec ? "blinkt" : "aus", gesperrt: rec || !aufnahmeMoeglich,
    hilfe: rec ? t("kanzel.wechselGesperrtHilfe") : aufnahme ? t("player.nichtBeiWiedergabe") : art !== "sender" ? t("player.keinSender")
      : !s.isPlaying ? t("player.keinPlay") : t("player.recStart"),
  };

  const stopp: Taste = { an: false, licht: "aus", gesperrt: !s.isPlaying && !s.isPaused && !rec,
    hilfe: t(s.weg?.aufnahme === false ? "kanzel.stoppHilfeOhneAufnahme" : "kanzel.stoppHilfe") };

  const kann = kannModusWechseln(s);
  const stromModus = s.playerMode === "hls" || s.playerMode === "direct";
  const modus: Tasten["modus"] = {
    an: false, licht: modusWechselt ? "atmet" : stromModus && art === "sender" ? "an" : "aus", gesperrt: !kann || modusWechselt,
    symbol: s.playerMode === "hls" ? "fa-arrows-rotate" : "fa-wave-square",
    farbe: s.playerMode === "hls" ? "gruen" : "gelb",
    hilfe: rec ? t("player.recModuswechsel") : modusWechselt ? t("player.moduswechsel") : !kann ? t("player.moduswechselNicht")
      : s.playerMode === "hls" ? t("player.directMode") : t("player.hlsMode"),
  };

  const mitListe = s.playerMode === "podcast" || aufnahme;
  const r = REIHENFOLGE[s.playMode] ?? REIHENFOLGE.linear;
  const reihenfolge: Tasten["reihenfolge"] = {
    an: false, licht: mitListe ? "an" : "aus", gesperrt: !mitListe, symbol: r.symbol, farbe: r.farbe,
    hilfe: mitListe ? t(r.text) : t("player.wiedergabeModus"),
  };

  // Fokus auf den laufenden Sender: ein Schalter, das blaue Licht heißt ein (RAD-19, Nutzer 20.11.2026); immer schaltbar,
  // auch bevor etwas spielt. Nach einem Fehler beim Sender (Codec, Verbindung) wählt dieselbe Taste eine andere Variante.
  const varianten = fehler && art === "sender";
  const quelle: Tasten["quelle"] = {
    an: false, licht: varianten ? "atmet" : fokusAn ? "an" : "aus", gesperrt: false, varianten,
    hilfe: varianten ? t("kanzel.andereVariante") : fokusAn ? t("kanzel.fokusAn") : t("kanzel.fokusAus"),
  };

  return {
    quelle,
    zurueck: blatt(-1),
    stopp,
    spielen,
    aufnahme: aufnehmen,
    vor: { ...blatt(1), gespiegelt: s.playMode === "reverse" },
    modus,
    reihenfolge,
  };
}

/** Nächste Reihenfolge der Wiedergabe: linear, rückwärts, Schleife, Zufall, wieder linear */
export function naechsteReihenfolge(jetzt: string): string {
  const i = REIHENFOLGEN.indexOf(jetzt as (typeof REIHENFOLGEN)[number]);
  return REIHENFOLGEN[(i + 1) % REIHENFOLGEN.length];
}

// ═══ Zeilen unter Quelle und Zeit ═══

export interface Spulstand {
  /** gefüllter Teil des Balkens in Prozent: Puffer im Zeitversatz, sonst die Position */
  fuellung: number;
  /** Breite der bedienbaren Bahn in Prozent: im Zeitversatz nur über den Puffer */
  bahn: number;
  text: string;
  /** Schrittweite des Reglers in Prozent */
  schritt: number;
  gesperrt: boolean;
}

/** Ohne Zeitversatz und ohne Position (nichts gewählt, direkter Strom): die Zeile steht trotzdem, ganz gesperrt
 *  (Nutzer 20.11.2026: "das immer einblenden, auch bei inaktivität", "aber als inaktiv") */
export const SPUL_RUHE: Spulstand & { live: boolean; max: string } = { fuellung: 0, bahn: 100, text: "--:--", schritt: 1, gesperrt: true, live: false, max: "--" };

/** Zeitversatz: wie viel gepuffert ist (von höchstens), Spulen nur über die Segmente */
export function zeitversatzStand(s: Stand, t: Uebersetzer): Spulstand & { live: boolean; max: string } {
  const hls = s.hlsStatus;
  const gepuffert = hls?.buffered_seconds || 0;
  const max = (hls?.max_segments || 0) * (hls?.segment_duration || 1);
  const bereich = hls?.last_segment != null && hls?.first_segment != null ? hls.last_segment - hls.first_segment : 0;
  const puffer = max > 0 ? Math.min(100, (gepuffert / max) * 100) : 0;
  return {
    fuellung: puffer,
    bahn: puffer,
    text: t("kanzel.von", { a: formatTimeShort(gepuffert), b: formatTimeShort(max) }),
    max: formatTimeShort(max),
    schritt: bereich > 0 && !s.isLive ? 100 / bereich : 0.1,
    gesperrt: s.isRecording || bereich <= 0,
    live: s.isLive,
  };
}

/** Position einer Folge oder Aufnahme */
export function positionStand(s: Stand, t: Uebersetzer): Spulstand {
  return {
    fuellung: s.dauer > 0 ? Math.min(100, Math.max(0, s.lage)) : 0,
    bahn: 100,
    text: t("kanzel.von", { a: formatTimeShort(s.zeit), b: formatTimeShort(s.dauer) }),
    schritt: 0.1,
    gesperrt: s.isRecording || !(s.dauer > 0),
  };
}

// ═══ Bitrate des Zeitversatzes ═══ Drehwahl in der Steuerung (Nutzer 17.11.2026: klein und gerätetypisch, keine Reihe
// gleichförmiger Tasten): erste Stellung "wie gesendet", dann die Stufen. Bedienbar nur, solange der Zeitversatz
// puffert; bei Aufnahme gesperrt, bei einer Folge im Puffer fest 128, sonst gesperrt (wie die Leuchten der alten Leiste).

export const BITRATEN = [32, 48, 64, 96, 128, 192, 256, 320] as const;

export type BitrateLage = "frei" | "gesperrt" | "fest" | "aus";

export function bitrateLage(s: Stand): BitrateLage {
  if (s.currentEpisode && s.playerMode === "hls") return "fest";
  if (hatZeitversatz(s) && s.hlsActive && !s.isRecording) return "frei";
  if (hatZeitversatz(s) && s.isRecording) return "gesperrt";
  return "aus";
}

/** Stellungen der Drehwahl als Raster des Appkerns ("|"-getrennt) */
export const bitrateRaster = (t: Uebersetzer): string => [t("kanzel.bitrateWieGesendetName"), ...BITRATEN.map(String)].join("|");

/** Stellung der Drehwahl für eine Vorgabe (0: wie gesendet) und zurück */
export function bitrateStellung(vorgabe: number | null): number {
  const i = vorgabe === null ? -1 : BITRATEN.indexOf(vorgabe as (typeof BITRATEN)[number]);
  return i < 0 ? 0 : i + 1;
}
export function bitrateAusStellung(stellung: number): number | null {
  return stellung >= 1 && stellung <= BITRATEN.length ? BITRATEN[stellung - 1] : null;
}

/** Leuchtschrift im Glas: welche Bitrate der Zeitversatz nimmt (nur Zustand, keine Bedienung) */
export function bitrateText(s: Stand, vorgabe: number | null, wechselt: boolean, t: Uebersetzer): string | null {
  const lage = bitrateLage(s);
  if (lage === "aus" || lage === "gesperrt") return null;
  if (wechselt) return t("kanzel.pufferWechselt");
  if (lage === "fest") return t("kanzel.pufferBitrate", { wert: t("kanzel.kbit", { n: 128 }) });
  return t("kanzel.pufferBitrate", { wert: vorgabe !== null ? t("kanzel.kbit", { n: vorgabe }) : t("kanzel.bitrateWieGesendet") });
}
