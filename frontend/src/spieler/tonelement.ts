// Das eine Tonelement der Seite (RAD-28): Rechner und Telefon wechseln beim Ändern der Fenstergröße die ganze Ansicht;
// hätte jede ihr eigenes Element, risse der Ton bei jedem Wechsel ab. Es lebt deshalb außerhalb der Ansichten, ist
// einmal an die Engine gebunden, und die Ansichten hängen nur ihre Ereignisse an (und beim Abbau wieder ab).
import * as engine from "../lib/playerEngine.js";
import { appState } from "../lib/store.svelte.js";
import { stummVerbinden } from "../lib/stumm";

let element: HTMLAudioElement | null = null;

export function tonelement(): HTMLAudioElement {
  if (element) return element;
  // ohne crossorigin: Ströme kommen in Basic direkt vom Sender, und die meisten Sender schicken keine CORS-Kopfzeilen;
  // mit dem Merkmal verweigerte der Browser sie ganz (RAD-10)
  const neu = document.createElement("audio");
  neu.preload = "none";
  neu.hidden = true;
  neu.addEventListener("ended", () => engine.handleEnded());
  neu.addEventListener("error", (e) => engine.handleError(e));
  document.body.append(neu);
  engine.init(neu, appState);
  stummVerbinden(neu);
  element = neu;
  return neu;
}

type Ereignisse = Partial<Record<keyof HTMLMediaElementEventMap, (e: Event) => void>>;

/** Ereignisse für die Lebensdauer einer Ansicht anhängen; liefert das Abhängen (für die Rückgabe eines $effect). */
export function anhaengen(ereignisse: Ereignisse): () => void {
  const ton = tonelement();
  const paare = Object.entries(ereignisse) as [string, (e: Event) => void][];
  for (const [name, f] of paare) ton.addEventListener(name, f);
  return () => { for (const [name, f] of paare) ton.removeEventListener(name, f); };
}
