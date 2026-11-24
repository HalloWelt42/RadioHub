<script lang="ts">
  // Meldung der App (appState.toast: Text und Art) in der Form des Rückgängig-Bands; am Rechner fährt sie als Lasche über
  // der Lautstärke aus der Kanzel (RAD-74, Stil in bausteine.css), am Telefon schwebt sie über dem Spieler. Wie lange sie steht, regelt der Zustand (actions.showToast).
  // Ohne Meldung steht dort der Hinweis auf eine neue Version (RAD-20): neu laden nur auf Wunsch, oder später. Vor
  // beiden steht "Werbung übersprungen" mit Zurück (RAD-32), solange er gilt.
  import { appState } from "../lib/store.svelte.js";
  import { pufferansicht } from "../spieler/pufferansicht.svelte";
  import { t } from "../lib/i18n.svelte.js";
  import { aktualisierung, neuLaden, spaeter } from "../lib/aktualisierung.svelte.js";
  import { werbehinweis } from "../spieler/werbehinweis.svelte";
  import { puffer } from "../spieler/puffer.svelte";
  import { bei } from "../lib/radio/abschnitte";

  const SYMBOL: Record<string, string> = {
    success: "fa-circle-check", error: "fa-circle-exclamation", warning: "fa-triangle-exclamation", info: "fa-circle-info",
  };
  const dauerKurz = (s: number) => `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, "0")}`;
  const meldung = $derived(appState.toast as { message: string; type?: string } | null);

  // Jede Meldung lässt sich mit dem X ausblenden (RAD-74). Ein Werbehinweis bleibt weg, solange dieselbe Stelle gilt.
  let werbungWeg = $state<string | null>(null);
  const werbeSchluessel = (w: { art: string; dauer: number | null; werbender?: string; herkunft: string }) =>
    `${w.art}|${w.dauer ?? ""}|${w.werbender ?? ""}|${w.herkunft}`;

  // Nach dem Start einer Aufnahme aus dem Zeitversatz (RAD-46): ab welchem Titel und wie viel aus dem Puffer kam; steht,
  // bis man es schließt, höchstens 20 Sekunden
  const AUFNAHME_HINWEIS_MS = 20000;
  let weg = $state<string | null>(null);
  const aufnahmeHinweis = $derived.by(() => {
    const sitzung = appState.recordingSession as string | null, vorlauf = appState.recordingVorlaufS as number;
    if (!appState.isRecording || !sitzung || !(vorlauf > 0) || weg === sitzung) return null;
    const a = bei(puffer.abschnitte, puffer.ende - (appState.recordingElapsed as number));
    return { sitzung, vorlauf, titel: a?.titel ?? "" };
  });
  // die Frist hängt an der Aufnahme, nicht am Hinweis: der rechnet mit der laufenden Zeit und begänne sie sonst jede Sekunde neu (RAD-139)
  const hinweisSitzung = $derived(aufnahmeHinweis?.sitzung ?? null);
  $effect(() => {
    const s = hinweisSitzung;
    if (!s) return;
    const uhr = setTimeout(() => (weg = s), AUFNAHME_HINWEIS_MS);
    return () => clearTimeout(uhr);
  });
</script>

{#snippet zu(schliessen: () => void)}
  <button class="rund rh-band-zu" type="button" aria-label={t("schale.schliessen")} title={t("schale.schliessen")} onclick={schliessen}><i class="fa-solid fa-xmark"></i></button>
{/snippet}

{#if werbehinweis.jetzt && werbeSchluessel(werbehinweis.jetzt) !== werbungWeg}
  {@const w = werbehinweis.jetzt}
  {@const wer = w.werbender || t(`schale.werbeherkunft_${w.herkunft}`)}
  <div class="rh-band rh-werbehinweis" role="status" aria-live="polite">
    {#if w.art === "verbinden"}
      <i class="fa-solid fa-rectangle-ad"></i><span><b>{t("schale.werbungVerbinden")}</b>{" "}<span class="rh-werbe-mehr">({w.dauer ? `${dauerKurz(w.dauer)}, ` : ""}{wer})</span>:
        {w.rest == null ? t("schale.werbungNichtGespieltOffen") : t("schale.werbungNichtGespielt")}{#if w.rest != null}{" "}<b class="rh-zahl">{dauerKurz(w.rest)}</b>{/if}</span>
      <button class="knopf" type="button" onclick={w.anhoeren}><i class="fa-solid fa-volume-high"></i>{t("schale.werbungTrotzdem")}</button>
    {:else if w.art === "stumm"}
      <i class="fa-solid fa-volume-xmark"></i><span><b>{t("schale.werbungLaeuft")}</b>{" "}<span class="rh-werbe-mehr">({wer})</span>:
        {#if w.rest == null}{t("schale.werbungStummOffen")}{:else}{t("schale.werbungStumm")}{" "}<b class="rh-zahl">{dauerKurz(w.rest)}</b><span class="rh-werbe-mehr">, {t("schale.werbungDannTon")}</span>{/if}</span>
      <button class="knopf" type="button" onclick={w.anhoeren}><i class="fa-solid fa-volume-high"></i>{t("schale.werbungTonAn")}</button>
    {:else}
      <i class="fa-solid fa-forward"></i><span><b>{t("schale.werbungUebersprungen")}</b>{" "}<span class="rh-werbe-mehr">({w.dauer ? `${dauerKurz(w.dauer)}, ` : ""}{wer})</span></span>
      <button class="knopf" type="button" onclick={w.anhoeren}><i class="fa-solid fa-rotate-left"></i>{t("schale.werbungAnhoeren")}</button>
    {/if}
    {@render zu(w.schliessen ?? (() => (werbungWeg = werbeSchluessel(w))))}
  </div>
{:else if aufnahmeHinweis}
  {@const h = aufnahmeHinweis}
  <div class="rh-band rh-aufnahmehinweis" role="status" aria-live="polite">
    <i class="fa-solid fa-circle"></i><span><b>{t("puffer.aufnahmeAb", { titel: h.titel })}</b>: {t("puffer.aufnahmeAbText", { vorlauf: dauerKurz(h.vorlauf) })}</span>
    <button class="knopf" type="button" title={t("puffer.beginnAendernHilfe")} onclick={() => { weg = h.sitzung; pufferansicht.oeffnen(); }}><i class="fa-solid fa-list-ul"></i>{t("puffer.beginnAendern")}</button>
    {@render zu(() => (weg = h.sitzung))}
  </div>
{:else if meldung}
  <div class="rh-band" class:gut={meldung.type === "success"} class:fehler={meldung.type === "error"} role="status" aria-live="polite">
    <i class="fa-solid {SYMBOL[meldung.type ?? 'info'] ?? SYMBOL.info}"></i><span>{meldung.message}</span>
    {@render zu(() => (appState.toast = null))}
  </div>
{:else if aktualisierung.neu && !aktualisierung.spaeter}
  <div class="rh-band" role="status" aria-live="polite">
    <i class="fa-solid fa-rotate"></i><span>{t("schale.neueFassung")}</span>
    <button class="knopf primaer" type="button" onclick={neuLaden}><i class="fa-solid fa-rotate"></i>{t("schale.neuLaden")}</button>
    <button class="knopf still" type="button" onclick={spaeter}>{t("schale.spaeter")}</button>
    {@render zu(spaeter)}
  </div>
{/if}
