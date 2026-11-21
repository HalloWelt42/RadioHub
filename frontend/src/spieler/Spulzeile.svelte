<script lang="ts">
  // Zeile unter Quelle und Zeit (Entwurf: rh-puffer-zeile): links und rechts je ein Knopf, dazwischen der Balken mit
  // Angabe. Im Zeitversatz ist der Balken der Puffer, bei Folgen und Aufnahmen die Position; über ihm liegt ein Regler zum
  // Spulen. Ziehen hält die Anzeige an, Loslassen (oder Pfeiltasten) springt über die Engine an die neue Stelle.
  import type { Snippet } from "svelte";
  import type { Spulstand } from "./kanzel";
  import type { Wiedergabe } from "./wiedergabe.svelte";

  let { stand, wiedergabe, hilfe, links, rechts, marken = [] }: {
    stand: Spulstand;
    wiedergabe: Wiedergabe;
    hilfe: string;
    links: Snippet;
    rechts: Snippet;
    /** Abschnitte in Prozent, etwa Werbestellen einer Folge (RAD-32) */
    marken?: { von: number; breite: number }[];
  } = $props();
</script>

<div class="rh-puffer-zeile">
  {@render links()}
  <div class="rh-puffer" title={hilfe}>
    <div class="rh-spulbahn" class:sucht={wiedergabe.sucht}>
      <div class="balken"><span style:width="{stand.fuellung}%"></span>
        {#each marken as m (m.von)}<i class="rh-werbemarke" style:left="{m.von}%" style:width="{m.breite}%"></i>{/each}</div>
      <input class="rh-spulregler" type="range" min="0" max="100" step={stand.schritt} value={wiedergabe.lage} aria-label={hilfe}
        aria-valuetext={stand.text} style:inline-size="{stand.bahn}%" disabled={stand.gesperrt || wiedergabe.sucht}
        onpointerdown={() => wiedergabe.ziehenBeginnen()}
        onpointerup={() => wiedergabe.freigeben()}
        onpointercancel={() => wiedergabe.freigeben()}
        oninput={(e) => wiedergabe.ziehen(Number(e.currentTarget.value))}
        onchange={() => wiedergabe.springen()} />
    </div>
    <span>{stand.text}</span>
  </div>
  {@render rechts()}
</div>
