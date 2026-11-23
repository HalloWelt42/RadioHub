<script lang="ts" module>
  export interface Lesezeile {
    nr: number;
    /** Uhrzeit oder Stelle, wie sie davor steht */
    zeit: string;
    /** maschinenlesbar, wenn es eine Uhrzeit ist */
    datetime?: string;
    text: string;
    /** klein darunter, etwa das Original */
    klein?: string;
    sprecher?: string;
  }
</script>

<script lang="ts">
  // Laufender Text in lesbarer Breite (RAD-129, RAD-130, RAD-22): Live mitlesen und Transkripte der Folgen. Er rollt nur in sich und
  // läuft mit, dem neuesten Text (`folgtAktiv` aus) oder der aktiven Zeile; bis man selbst rollt. Text ist frei wählbar.
  import { tick } from "svelte";

  let { zeilen, aktiv = null, folgtAktiv = false, mitlaufen = $bindable(true), leer, beschriftung, onzeit }: {
    zeilen: Lesezeile[];
    /** die Zeile, die gerade gesprochen oder gehört wird */
    aktiv?: number | null;
    folgtAktiv?: boolean;
    mitlaufen?: boolean;
    leer: string;
    beschriftung: string;
    /** Klick auf die Zeit einer Zeile */
    onzeit?: (nr: number) => void;
  } = $props();

  const NAH_PX = 32;
  /** so weit von oben steht die aktive Zeile */
  const LESEHOEHE = 0.15;
  let feld = $state<HTMLElement>();
  /** von Hand weggerollt (nicht über die Taste angehalten) */
  let weg = false;

  $effect(() => {
    void folgtAktiv;                  // ein anderes Ziel: gleich dorthin, auch wenn man gerade woanders las
    weg = false;
    mitlaufen = true;
  });
  $effect(() => {
    void [zeilen, aktiv, folgtAktiv];
    if (mitlaufen) void tick().then(folgen);
  });
  function folgen() {
    if (!feld) return;
    if (!folgtAktiv) return void (feld.scrollTop = feld.scrollHeight);
    const p = feld.querySelector("p.spricht");
    if (p) feld.scrollTop += p.getBoundingClientRect().top - feld.getBoundingClientRect().top - feld.clientHeight * LESEHOEHE;
  }
  // Am Ende sagt die Stelle, ob man mitläuft: unten angekommen wieder. Folgt es der aktiven Zeile, rollt es auch selbst, dann zählt die Hand.
  function gerollt() {
    if (!feld || folgtAktiv) return;
    const amEnde = feld.scrollHeight - feld.scrollTop - feld.clientHeight < NAH_PX;
    if (!amEnde && mitlaufen) { weg = true; mitlaufen = false; }
    else if (amEnde && weg) { weg = false; mitlaufen = true; }
  }
  function vonHand(e: Event) {
    const taste = e instanceof KeyboardEvent ? /^(Arrow|Page|Home|End)/.test(e.key) : e.type !== "pointerdown" || e.target === feld;
    if (folgtAktiv && taste) mitlaufen = false;
  }
  /** was man im Feld markiert hat, leer ohne */
  export function markiert(): string {
    const auswahl = getSelection();
    return auswahl && !auswahl.isCollapsed && feld?.contains(auswahl.anchorNode) ? auswahl.toString() : "";
  }
</script>

<!-- svelte-ignore a11y_no_noninteractive_tabindex, a11y_no_noninteractive_element_interactions -->
<div class="rh-mitlese-feld" bind:this={feld} onscroll={gerollt} onwheel={vonHand} ontouchmove={vonHand} onkeydown={vonHand} onpointerdown={vonHand}
     role="log" tabindex="0" aria-label={beschriftung}>
  {#each zeilen as z (z.nr)}
    <p class:spricht={aktiv === z.nr}>
      {#if onzeit}<button class="rh-mitlese-zeit" type="button" onclick={() => onzeit(z.nr)}>{z.zeit}</button>{:else}<time datetime={z.datetime}>{z.zeit}</time>{/if}
      <span>{#if z.sprecher}<b class="rh-mitlese-sprecher">{z.sprecher}</b>{/if}{z.text}</span>
      {#if z.klein}<span class="rh-mitlese-original">{z.klein}</span>{/if}</p>
  {:else}
    <p class="rh-mitlese-leer">{leer}</p>
  {/each}
</div>
