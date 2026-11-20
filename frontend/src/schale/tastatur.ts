// Tastatur am Rechner, gemeinsam für beide Bauziele (volle App und Webversion, RAD-4): Leertaste wie die Taste Spielen
// (spielen, Pause, weiter), S beendet, Pfeile für Lautstärke und Sender, M stumm, die Ziffern 1 bis n wählen die
// angebotenen Bereiche in der Reihenfolge der Navigation. Bei laufender Aufnahme sind Anhalten, Beenden und
// Senderwechsel gesperrt. In Eingabefeldern und am Telefon gilt nichts davon.
import { actions, appState } from "../lib/store.svelte.js";
import { spielenOderPause } from "../spieler/aktionen";

export function tasteDerApp(e: KeyboardEvent, bereiche: readonly string[]): void {
  const ziel = e.target as HTMLElement;
  if (ziel.tagName === "INPUT" || ziel.tagName === "TEXTAREA" || ziel.tagName === "SELECT" || ziel.isContentEditable) return;
  const aufnahme = appState.isRecording;
  const ziffer = Number(e.key);
  if (Number.isInteger(ziffer) && ziffer >= 1 && ziffer <= bereiche.length && !e.ctrlKey && !e.metaKey && !e.altKey) {
    actions.setTab(bereiche[ziffer - 1]);
    return;
  }
  switch (e.key) {
    case " ":
      e.preventDefault();
      if (!aufnahme) spielenOderPause();
      break;
    case "s":
      if (!aufnahme && !e.ctrlKey && !e.metaKey) actions.stop();
      break;
    case "ArrowUp":
      e.preventDefault();
      actions.setVolume(Math.min(100, appState.volume + 5));
      break;
    case "ArrowDown":
      e.preventDefault();
      actions.setVolume(Math.max(0, appState.volume - 5));
      break;
    case "ArrowLeft":
      e.preventDefault();
      if (!aufnahme) actions.navigatePrev();
      break;
    case "ArrowRight":
      e.preventDefault();
      if (!aufnahme) actions.navigateNext();
      break;
    case "m":
      if (!e.ctrlKey && !e.metaKey) actions.setVolume(appState.volume > 0 ? 0 : 70);
      break;
  }
}
