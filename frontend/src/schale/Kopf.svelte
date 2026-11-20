<script lang="ts">
  // Kopf am Rechner wie im Entwurf (mockups/radio-filter/rechner.html): Schriftzug RadioHub mit Herz (führt zum
  // Unterstützen), Pillen-Navigation mit Tastenlicht, die in den Inhalt ragt, Status (Dienst und Ablage) und die Tafel
  // Darstellung mit Konto. Das Tastenlicht zeigt, welcher Bereich gerade spielt (blau) oder aufnimmt (rot). Die
  // Webversion (RAD-4) zeigt nur Radio und Einstellungen, ohne Status, Konto und Unterstützen (ohne Backend).
  import { appState, actions } from "../lib/store.svelte.js";
  import { t } from "../lib/i18n.svelte.js";
  import * as sfx from "../lib/uiSounds.js";
  import Darstellung from "./Darstellung.svelte";
  import Konto from "./Konto.svelte";

  type Bereich = "radio" | "recordings" | "podcasts" | "settings";
  let { online, ablage, bereiche = ["radio", "recordings", "podcasts", "settings"], backend = true }: {
    online?: boolean | null;
    ablage?: { verbunden: boolean; meldung?: string } | null;
    /** angebotene Bereiche in der Navigation */
    bereiche?: Bereich[];
    /** mit Backend: Status von Dienst und Ablage, Konto, Unterstützen */
    backend?: boolean;
  } = $props();

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

  let offen = $state(false);
  let darstellungsKnopf = $state<HTMLElement>();
  let tafel = $state<HTMLElement>();

  // Tafel schließt bei Klick daneben und mit Escape
  function daneben(e: MouseEvent) {
    if (!offen) return;
    const ziel = e.target as Node;
    if (tafel?.contains(ziel) || darstellungsKnopf?.contains(ziel)) return;
    offen = false;
  }
  function taste(e: KeyboardEvent) {
    if (offen && e.key === "Escape") {
      offen = false;
      darstellungsKnopf?.focus();
    }
  }
</script>

<svelte:window onclick={daneben} onkeydown={taste} />

<header class="rh-kopf">
  <div class="rh-marke">
    <span class="rh-marke-zeile"><a class="rh-logo" href="/radio" onclick={(e) => { e.preventDefault(); actions.navigateTo("/radio"); }}>RadioHub</a>
      {#if backend}<button class="rh-herz" type="button" title={t("app.unterstuetzenTitle")} aria-label={t("app.unterstuetzenTitle")}
              onclick={() => { actions.navigateTo("/einstellungen/allgemein/bedanken"); sfx.select(); }}><i class="fa-solid fa-heart"></i></button>{/if}</span>
    <span class="rh-unterzeile">{t("app.digitalAudioSystem")}</span>
  </div>
  <nav class="rh-nav" aria-label={t("schale.bereiche")}><div class="rh-nav-schiene">
    {#each BEREICHE as b, i (b.id)}
      {@const l = licht(b.id)}
      <button class="rh-nav-knopf" type="button" aria-current={aktiv(b.id) ? "page" : undefined} title="{t(b.text)} ({i + 1})"
              onclick={() => { actions.setTab(b.id); sfx.select(); }} onmouseenter={sfx.hoverSoft}>
        <ak-led art="schlitz" farbe={l.farbe} zustand={l.zustand}></ak-led><i class="fa-solid {b.symbol}"></i><span>{t(b.text)}</span>
      </button>
    {/each}
  </div></nav>
  <div class="rh-kopf-rechts">
    {#if backend}
    <div class="rh-status">
      <!-- die Leuchte schreibt ihren Text einmal; ändert er sich, entsteht sie neu -->
      {#key online}<ak-led farbe={online === false ? "rot" : "gruen"} zustand={online === null ? "aus" : "an"} text={online === false ? t("nav.offline") : t("nav.online")}
              hilfe={online === false ? t("schale.dienstWeg") : t("schale.dienstDa")}></ak-led>{/key}
      {#if ablage}
        <ak-led farbe={ablage.verbunden ? "gruen" : "rot"} zustand="an" text={t("nav.ablage")}
                hilfe={ablage.verbunden ? t("schale.ablageDa") : (ablage.meldung || t("schale.ablageWeg"))}></ak-led>
      {/if}
    </div>
    {/if}
    <div class="rh-darstellung">
      <button class="knopf" type="button" bind:this={darstellungsKnopf} aria-controls="tafel-darstellung" aria-expanded={offen}
              title={t("schale.darstellungTitel")} onclick={() => (offen = !offen)}><i class="fa-solid fa-circle-half-stroke"></i><span>{t("schale.darstellung")}</span></button>
      <div class="rh-tafel" id="tafel-darstellung" role="dialog" aria-label={t("schale.darstellung")} hidden={!offen} bind:this={tafel}>
        <Darstellung />
        {#if backend}<Konto />{/if}
      </div>
    </div>
  </div>
</header>
