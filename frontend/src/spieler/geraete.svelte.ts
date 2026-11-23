// Übergabe zwischen Geräten im Radio (RAD-18): dieses Fenster meldet beim Vermittler (Baustein Uebergabe des Appkerns,
// Backend app/geraete.py), was es spielt, und spielt, was ein anderes Gerät hergibt. Holen bittet das andere Gerät um
// seine Wiedergabe, Dorthin gibt die eigene ab und hält hier an. Was mitreist, ist die Quelle, wie die Oberfläche sie
// zum Abspielen braucht (ohne lange Texte), dazu die Stelle bei Folgen und Aufnahmen; ein Sender geht live weiter.
// Nur mit Backend (PRO); die Webversion hat keinen Vermittler.
import { Uebergabe } from "appkern-oberflaeche";
import * as engine from "../lib/playerEngine.js";
import { actions } from "../lib/store.svelte.js";
import { app } from "./app";
import { t } from "../lib/i18n.svelte.js";
import { tonelement } from "./tonelement";
import { lautstaerke, spielenOderPause } from "./aktionen";
import { beschreibung } from "../lib/telefon/medien.js";
import { wunsch } from "../lib/telefon/verbindung.svelte.js";

export { kompakt, paketJetzt, zustandJetzt, type Fernaktion, type Quellart, type RadioPaket, type RadioZustand } from "./geraetepaket";
import { paketJetzt, zustandJetzt, type Fernaktion, type RadioPaket, type RadioZustand } from "./geraetepaket";

/** ein Paket hier spielen, mit denselben Wegen wie ein Klick in der Liste */
export function paketSpielen(p: RadioPaket): void {
  if (p.art === "sender" && p.sender) void actions.playStation(p.sender);
  else if (p.art === "folge" && p.folge) void engine.playPodcast({ ...p.folge, resume_position: p.stelle }, p.podcast ?? null);
  else if (p.art === "aufnahme" && p.aufnahme) void engine.playRecording(p.aufnahme, p.stelle);
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
