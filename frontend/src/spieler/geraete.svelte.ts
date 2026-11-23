// Übergabe zwischen Geräten im Radio (RAD-18): dieses Fenster meldet beim Vermittler (Baustein Uebergabe des Appkerns,
// Backend app/geraete.py), was es spielt, und spielt, was ein anderes Gerät hergibt. Holen bittet das andere Gerät um
// seine Wiedergabe, Dorthin gibt die eigene ab und hält hier an. Was mitreist, ist die Quelle, wie die Oberfläche sie
// zum Abspielen braucht (ohne lange Texte), dazu die Stelle bei Folgen und Aufnahmen; ein Sender geht live weiter.
// Nur mit Backend (PRO); die Webversion hat keinen Vermittler.
import { Uebergabe } from "appkern-oberflaeche";
import * as engine from "../lib/playerEngine.js";
import { actions, appState } from "../lib/store.svelte.js";
import { aufnahmequelle, reiheVon, type Spieleintrag } from "../lib/aufnahmen";
import { app } from "./app";
import { t } from "../lib/i18n.svelte.js";
import { tonelement } from "./tonelement";
import { lautstaerke, spielenOderPause, zurQuelle } from "./aktionen";
import { beschreibung } from "../lib/telefon/medien.js";
import { wunsch } from "../lib/telefon/verbindung.svelte.js";

export { kompakt, paketJetzt, zustandJetzt, type Fernaktion, type Quellart, type RadioPaket, type RadioZustand } from "./geraetepaket";
import { paketJetzt, zustandJetzt, type Fernaktion, type RadioPaket, type RadioZustand } from "./geraetepaket";

/** Eine Aufnahme liegt zentral: das empfangende Gerät holt sich ihre Titelreihe selbst, damit es danach weitergeht (RAD-134) */
async function aufnahmeSpielen(a: Spieleintrag, stelle: number): Promise<void> {
  const zustand = appState as unknown as { recordingPlaylist: Spieleintrag[] };
  zustand.recordingPlaylist = [a];
  void engine.playRecording(a, stelle);
  if (!a.session_id || a.path.startsWith("sitzung:")) return;
  const reihe = await reiheVon(aufnahmequelle, a.session_id).catch(() => []);
  if (reihe.some((x) => x.path === a.path) && app.currentRecording?.path === a.path) zustand.recordingPlaylist = reihe;
}

/** ein Paket hier spielen, mit denselben Wegen wie ein Klick in der Liste */
export function paketSpielen(p: RadioPaket): void {
  if (p.art === "sender" && p.sender) void actions.playStation(p.sender);
  else if (p.art === "folge" && p.folge) void engine.playPodcast({ ...p.folge, resume_position: p.stelle }, p.podcast ?? null);
  else if (p.art === "aufnahme" && p.aufnahme) void aufnahmeSpielen(p.aufnahme as unknown as Spieleintrag, p.stelle);
}

/** Was ein anderes Gerät hier auslöst (RAD-96), mit denselben Wegen wie die Tasten. Eine laufende Aufnahme bleibt
 *  unberührt: Wechsel und Pause gibt es dann nicht, Stopp beendet nur das Hören. */
export function befehlAusfuehren(aktion: string, wert: number | null): void {
  const betrag = wert !== null && Number.isFinite(wert) ? wert : null;
  switch (aktion as Fernaktion) {
    case "umschalten":
      wunsch.spielen = !(app.isPlaying && !app.isPaused);   // sonst verbände der Wächter der Weckeransicht nach einer Pause neu
      spielenOderPause();
      break;
    case "stopp":
      wunsch.spielen = false;
      void engine.stop();
      break;
    case "weiter":
      if (!app.isRecording) void actions.navigateNext();
      break;
    case "vorher":
      if (!app.isRecording) void actions.navigatePrev();
      break;
    case "vor":
      if (betrag !== null) engine.skip(Math.abs(betrag));
      break;
    case "zurueck":
      if (betrag !== null) engine.skip(-Math.abs(betrag));
      break;
    case "lautstaerke":
      if (betrag !== null) lautstaerke(Math.max(0, Math.min(100, Math.round(betrag))));
      break;
  }
}

export const geraete = new Uebergabe<RadioZustand, RadioPaket>("/api/v1/geraete/ws", "radiohub");

/** Was die Ansicht nach einer Übergabe mitzieht (RAD-134): am Rechner zur Quelle springen; das Telefon setzt seinen Weg ein */
export interface Folgeweg {
  /** hierher gegeben: zeigen, was jetzt hier spielt */
  angekommen(): void;
  /** dorthin gegeben (oder von dort geholt): die Steuerung folgt dem Gerät `id` */
  abgegeben(id: string): void;
}
const VORGABE: Folgeweg = { angekommen: zurQuelle, abgegeben: () => undefined };
let folgeweg = VORGABE;
export function folgewegSetzen(weg: Folgeweg): () => void {
  folgeweg = weg;
  return () => { if (folgeweg === weg) folgeweg = VORGABE; };
}

const spieltSchon = (p: RadioPaket): boolean => (p.art === "sender" ? app.currentStation?.uuid === p.sender?.uuid
  : p.art === "folge" ? app.currentEpisode?.id === p.folge?.id : app.currentRecording?.path === p.aufnahme?.path);

/** sobald das Paket hier wirklich spielt (der Wechsel beendet erst das Bisherige), folgt die Ansicht */
function ansichtFolgt(p: RadioPaket, versuche = 50): void {
  if (spieltSchon(p)) return folgeweg.angekommen();
  if (versuche > 0) setTimeout(() => ansichtFolgt(p, versuche - 1), 100);
}

// wohin abgegeben wurde, sagt der Baustein seinem Weg nicht: hier steht es dabei
const dorthin = geraete.dorthin.bind(geraete);
geraete.dorthin = (id: string): boolean => {
  const gegeben = dorthin(id);
  if (gegeben) folgeweg.abgegeben(id);
  return gegeben;
};

/** Texte der Geräteliste in der Sprache der App */
export function geraeteTexte() {
  const k = ["titel", "hier", "diesesGeraet", "umbenennen", "name", "schliessen", "holen", "holenHilfe", "dorthin", "dorthinHilfe", "keins", "verbindet"] as const;
  return Object.fromEntries(k.map((n) => [n, t(`geraete.${n}`)])) as Record<(typeof k)[number], string>;
}

/** Zeile der Geräteliste zu einem Zustand */
export function geraeteZeile(z: RadioZustand | null): string {
  if (!z) return t("geraete.bereit");
  return t(z.laeuft ? "geraete.spielt" : "geraete.angehalten", { titel: z.titel });
}

/** beim Anmelden (nur mit Backend); liefert das Beenden (beim Abmelden) */
export function geraeteStarten(): () => void {
  if (!engine.faehigkeiten().uebergabe) return () => {};
  geraete.starten({
    paket: () => paketJetzt(app, tonelement().currentTime || 0),
    annehmen: (paket, von) => {
      paketSpielen(paket);
      ansichtFolgt(paket);
      actions.showToast(t("geraete.uebernommen", { von }), "success");
    },
    abgegeben: () => void engine.stop(),
    befehl: befehlAusfuehren,
  });
  const melden = $effect.root(() => {
    $effect(() => geraete.melden(zustandJetzt(app, beschreibung(app)?.bild ?? null)));
  });
  return () => {
    melden();
    geraete.beenden();
  };
}
