<script lang="ts">
  // Leere Liste der Folgen (RAD-149): sagt kurz, warum, und der ganze Hinweis ist der Knopf dorthin, wo es weitergeht. Rechner und
  // Telefon; die Regel steht in lib/podcasts/leer.
  import { t } from "../../lib/i18n.svelte.js";
  import type { Leerhinweis } from "../../lib/podcasts";

  let { hinweis, suche = "", onweiter, telefon = false }: { hinweis: Leerhinweis; suche?: string; onweiter: () => void; telefon?: boolean } = $props();
  const g = $derived(hinweis.grund);
</script>

<button class="rh-ohne-treffer rh-leerhinweis" class:telefon type="button" onclick={onweiter}>
  <i class="fa-solid {hinweis.symbol}" aria-hidden="true"></i>
  <b>{t(`podcastAnsicht.leer.${g}`, { text: suche.trim() })}</b>
  <span>{t(`podcastAnsicht.leer.${g}Hilfe`)}</span>
  <span class="knopf primaer">{t(`podcastAnsicht.leer.${g}Weiter`)}</span>
</button>
