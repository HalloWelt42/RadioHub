<script lang="ts">
  // Zeile unter Quelle und Zeit (Entwurf: rh-puffer-zeile): links und rechts je ein Knopf, dazwischen der Balken mit
  // Angabe. Im Zeitversatz ist der Balken der Puffer, bei Folgen und Aufnahmen die Position; über ihm liegt ein Regler zum
  // Spulen. Ziehen hält die Anzeige an, Loslassen (oder Pfeiltasten) springt über die Engine an die neue Stelle.
  // Im Zeitversatz (RAD-46, Entwurf puffer.html) zeigt der Balken die Titelgrenzen als Striche, Werbung violett, eine
  // laufende Aufnahme rot; beim Überfahren steht der Titel an der Stelle über dem Balken,
  // ein fertiger mit der Taste zum Speichern (RAD-132); der Hinweis bleibt, solange der Zeiger auf ihm steht.
  import type { Snippet } from "svelte";
  import type { Spulstand } from "./kanzel";
  import type { Wiedergabe } from "./wiedergabe.svelte";

  interface Hinweis { titel: string; text: string; links: number; taste?: { symbol: string; text: string; gesperrt: boolean; tun: () => void } }

  let { stand, wiedergabe, hilfe, links, rechts, marken = [], striche = [], aufnahme = null, tipp, einrasten }: {
    stand: Spulstand;
    wiedergabe: Wiedergabe;
    hilfe: string;
    links: Snippet;
    rechts: Snippet;
    /** Abschnitte in Prozent, etwa Werbestellen einer Folge (RAD-32) */
    marken?: { von: number; breite: number }[];
    /** Titelgrenzen in Prozent der Breite (RAD-46) */
    striche?: number[];
    /** Teil des Balkens, der gerade aufgenommen wird, in Prozent */
    aufnahme?: { von: number; breite: number } | null;
    /** was an einer Stelle des Balkens läuft (Prozent der Breite), für den Hinweis beim Überfahren */
    tipp?: (prozent: number) => Hinweis | null;
    /** Lage des Reglers beim Loslassen an eine nahe Titelgrenze ziehen */
    einrasten?: (lage: number) => number;
  } = $props();

  let balken = $state<HTMLDivElement>();
  let hinweisBei = $state<number | null>(null);
  const hinweis = $derived(tipp && hinweisBei !== null ? tipp(hinweisBei) : null);

  function zeigen(e: PointerEvent): void {
    if (!tipp || !balken || e.pointerType === "touch" || (e.target as HTMLElement).closest(".rh-balkentipp")) return;
    const r = balken.getBoundingClientRect();
    hinweisBei = r.width > 0 ? ((e.clientX - r.left) / r.width) * 100 : null;
  }

  function loslassen(): void {
    if (einrasten) wiedergabe.ziehen(einrasten(wiedergabe.lage));
    wiedergabe.springen();
  }
</script>

<div class="rh-puffer-zeile">
  {@render links()}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="rh-puffer" title={tipp ? undefined : hilfe} onpointermove={zeigen} onpointerleave={() => (hinweisBei = null)}>
    <div class="rh-spulbahn" class:sucht={wiedergabe.sucht}>
      <div class="balken" bind:this={balken}><span style:width="{stand.fuellung}%"></span>
        {#if aufnahme}<i class="rh-aufnahmemarke" style:left="{aufnahme.von}%" style:width="{aufnahme.breite}%"></i>{/if}
        {#each marken as m, i (i)}<i class="rh-werbemarke" style:left="{m.von}%" style:width="{m.breite}%"></i>{/each}</div>
      {#if striche.length}
        <div class="rh-titelstriche" aria-hidden="true">{#each striche as s, i (i)}<i style:left="{s}%"></i>{/each}</div>
      {/if}
      <input class="rh-spulregler" type="range" min="0" max="100" step={stand.schritt} value={wiedergabe.lage} aria-label={hilfe}
        aria-valuetext={stand.text} style:inline-size="{stand.bahn}%" disabled={stand.gesperrt || wiedergabe.sucht}
        onpointerdown={() => wiedergabe.ziehenBeginnen()}
        onpointerup={() => wiedergabe.freigeben()}
        onpointercancel={() => wiedergabe.freigeben()}
        oninput={(e) => wiedergabe.ziehen(Number(e.currentTarget.value))}
        onchange={loslassen} />
      {#if hinweis}
        <span class="rh-balkentipp" class:rechts={hinweis.links > 60} style:left="{hinweis.links}%" role="tooltip">
          <b>{hinweis.titel}</b><span>{hinweis.text}</span>
          {#if hinweis.taste}<button class="knopf rh-tipp-taste" type="button" disabled={hinweis.taste.gesperrt} onclick={hinweis.taste.tun}>
            <i class={hinweis.taste.symbol}></i>{hinweis.taste.text}</button>{/if}</span>
      {/if}
    </div>
    <span>{stand.text}</span>
  </div>
  {@render rechts()}
</div>
