<script lang="ts">
  // Kopf am Rechner wie im Entwurf (mockups/radio-filter/rechner.html): Schriftzug RadioHub mit Herz (führt zum
  // Unterstützen), Pillen-Navigation mit Tastenlicht, die in den Inhalt ragt, und rechts
  // die Bedienung (Thema, Schrift, Sprache, Abmelden; KopfBedienung, RAD-71). Das Tastenlicht zeigt, welcher Bereich gerade spielt (blau) oder aufnimmt (rot). Neben dem
  // Herz das Zeichen der Ausgabe (Nutzer 20.11.2026): PRO in Gold; die Basic-Webversion (RAD-4) zeigt BASIC in Silber,
  // das selbst zum Quellcode der PRO führt, dazu nur Radio und Einstellungen, ohne Konto; das Herz führt dort
  // zum Unterstützen.
  import { appState, actions } from "../lib/store.svelte.js";
  import { t } from "../lib/i18n.svelte.js";
  import KopfBedienung from "./KopfBedienung.svelte";
  import { PRO_QUELLCODE, UNTERSTUETZEN, type Ausgabe } from "../lib/ausgabe";

  type Bereich = "radio" | "recordings" | "podcasts" | "settings";
  let { bereiche = ["radio", "recordings", "podcasts", "settings"], ausgabe = "pro" }: {
    /** angebotene Bereiche in der Navigation */
    bereiche?: Bereich[];
    /** PRO mit Backend (Konto), Basic als Webversion ohne */
    ausgabe?: Ausgabe;
  } = $props();
  const backend = $derived(ausgabe === "pro");

  const ALLE = [
    { id: "radio", text: "schale.radio", symbol: "fa-radio" },
    { id: "recordings", text: "schale.aufnahmen", symbol: "fa-circle-dot" },
    { id: "podcasts", text: "schale.podcasts", symbol: "fa-podcast" },
    { id: "settings", text: "schale.einstellungen", symbol: "fa-sliders" },
  ] as const;
  const BEREICHE = $derived(ALLE.filter((b) => bereiche.includes(b.id)));

  // welcher Bereich die laufende Wiedergabe trägt
  const spielt = $derived(
    !appState.isPlaying && !appState.isPaused ? null
      : appState.playerMode === "podcast" ? "podcasts"
      : appState.playerMode === "recording" ? "recordings"
      : appState.playerMode === "hls" || appState.playerMode === "direct" ? "radio" : null,
  );

  function licht(id: string): { farbe: "rot" | "blau" | "gruen"; zustand: "an" | "aus" | "blinkt" } {
    if (id === "radio" && appState.isRecording) return { farbe: "rot", zustand: "blinkt" };
    if (spielt === id) return { farbe: "blau", zustand: "an" };
    return { farbe: "gruen", zustand: "aus" };
  }

  const aktiv = (id: string) => appState.activeTab === id || (id === "radio" && appState.activeTab === "wecker");
</script>

<header class="rh-kopf">
  <div class="rh-marke">
    <span class="rh-marke-zeile"><a class="rh-logo" href="/radio" aria-label="RadioHub" onclick={(e) => { e.preventDefault(); actions.navigateTo("/radio"); }}><!--
        Buchstaben einzeln für den Glanzlauf (RAD-71) -->{#each "RadioHub".split("") as zeichen, i (i)}<span class="rh-logo-zeichen" style:--i={i} aria-hidden="true">{zeichen}</span>{/each}</a>
      {#if backend}<button class="rh-herz" type="button" title={t("app.unterstuetzenTitle")} aria-label={t("app.unterstuetzenTitle")}
              onclick={() => { actions.navigateTo("/einstellungen/allgemein/bedanken"); }}><i class="fa-solid fa-heart"></i></button>
        <span class="rh-pro" title={t("schale.proTitel")}>PRO</span>
      {:else}<a class="rh-herz" href={UNTERSTUETZEN} target="_blank" rel="noopener" title={t("app.unterstuetzenTitle")} aria-label={t("app.unterstuetzenTitle")}><i class="fa-solid fa-heart"></i></a>
        <a class="rh-basic" href={PRO_QUELLCODE} target="_blank" rel="noopener" title={t("schale.basicVerweis")} aria-label={t("schale.basicVerweis")}>BASIC</a>{/if}</span>
    <span class="rh-unterzeile">{t("app.digitalAudioSystem")}</span>
  </div>
  <nav class="rh-nav" aria-label={t("schale.bereiche")}><div class="rh-nav-schiene">
    {#each BEREICHE as b, i (b.id)}
      {@const l = licht(b.id)}
      <button class="rh-nav-knopf" type="button" aria-current={aktiv(b.id) ? "page" : undefined} title="{t(b.text)} ({i + 1})"
              onclick={() => { actions.setTab(b.id); }}>
        <ak-led art="schlitz" farbe={l.farbe} zustand={l.zustand}></ak-led><i class="fa-solid {b.symbol}"></i><span>{t(b.text)}</span>
      </button>
    {/each}
  </div></nav>
  <div class="rh-kopf-rechts">
    <KopfBedienung konto={backend} />
  </div>
</header>
