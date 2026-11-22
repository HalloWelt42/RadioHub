<script lang="ts">
  // Meldung der App (appState.toast: Text und Art), schwebend über der Abspielleiste in der Form des Rückgängig-Bands
  // aus dem Entwurf; am Rechner und am Telefon dieselbe. Wie lange sie steht, regelt der Zustand (actions.showToast).
  // Ohne Meldung steht dort der Hinweis auf eine neue Version (RAD-20): neu laden nur auf Wunsch, oder später. Vor
  // beiden steht "Werbung übersprungen" mit Zurück (RAD-32), solange er gilt.
  import { appState, actions } from "../lib/store.svelte.js";
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
  $effect(() => {
    const s = aufnahmeHinweis?.sitzung;
    if (!s) return;
    const uhr = setTimeout(() => (weg = s), AUFNAHME_HINWEIS_MS);
    return () => clearTimeout(uhr);
  });
</script>

{#if werbehinweis.jetzt}
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
      {#if w.schliessen}<button class="rund" type="button" aria-label={t("schale.schliessen")} title={t("schale.schliessen")} onclick={w.schliessen}><i class="fa-solid fa-xmark"></i></button>{/if}
    {/if}
  </div>
{:else if aufnahmeHinweis}
  {@const h = aufnahmeHinweis}
  <div class="rh-band rh-aufnahmehinweis" role="status" aria-live="polite">
    <i class="fa-solid fa-circle"></i><span><b>{t("puffer.aufnahmeAb", { titel: h.titel })}</b>: {t("puffer.aufnahmeAbText", { vorlauf: dauerKurz(h.vorlauf) })}</span>
    <button class="knopf" type="button" title={t("puffer.beginnAendernHilfe")} onclick={() => { weg = h.sitzung; actions.navigateTo("/radio/puffer"); }}><i class="fa-solid fa-list-ul"></i>{t("puffer.beginnAendern")}</button>
    <button class="rund" type="button" aria-label={t("schale.schliessen")} title={t("schale.schliessen")} onclick={() => (weg = h.sitzung)}><i class="fa-solid fa-xmark"></i></button>
  </div>
{:else if meldung}
  <div class="rh-band" class:gut={meldung.type === "success"} class:fehler={meldung.type === "error"} role="status" aria-live="polite">
    <i class="fa-solid {SYMBOL[meldung.type ?? 'info'] ?? SYMBOL.info}"></i><span>{meldung.message}</span>
  </div>
{:else if aktualisierung.neu && !aktualisierung.spaeter}
  <div class="rh-band" role="status" aria-live="polite">
    <i class="fa-solid fa-rotate"></i><span>{t("schale.neueFassung")}</span>
    <button class="knopf primaer" type="button" onclick={neuLaden}><i class="fa-solid fa-rotate"></i>{t("schale.neuLaden")}</button>
    <button class="knopf still" type="button" onclick={spaeter}>{t("schale.spaeter")}</button>
  </div>
{/if}
