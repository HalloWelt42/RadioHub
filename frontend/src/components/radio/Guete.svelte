<script lang="ts">
  // Qualität als Lichterleiste hinter Glas: vier Lichter, Farbe je Stufe, unbekannt schraffiert
  import { QUALITAET, qualitaetName } from "../../lib/radio/anzeige";
  import { t } from "../../lib/i18n.svelte.js";
  import type { Qualitaet } from "../../lib/radio/typen";

  let { stufe }: { stufe: Qualitaet } = $props();
  const q = $derived(QUALITAET[stufe] ?? QUALITAET.unbekannt);
</script>

<span class="rh-guete" data-guete={stufe} style="--farbe:var(--led-{q.farbe})" title={t(`radio.qualitaetHilfe.${stufe}`)} role="img"
      aria-label="{t('radio.qualitaetLabel')} {qualitaetName(stufe)}">{#each [0, 1, 2, 3] as i (i)}<i class:an={i < q.lichter}></i>{/each}</span>
