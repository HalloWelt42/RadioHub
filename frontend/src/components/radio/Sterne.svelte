<script lang="ts">
  // Eigene Bewertung als Sterne (1 bis 3)
  import { t } from "../../lib/i18n.svelte.js";

  let { n }: { n: number } = $props();
</script>

<span class="rh-sterne" aria-label={t("radio.sterneVon", { n })}>{#each [1, 2, 3] as i (i)}<i class="fa-solid fa-star" class:aus={i > n}></i>{/each}</span>
