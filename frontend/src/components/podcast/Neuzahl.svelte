<script lang="ts">
  // Zahl der ungehörten Folgen mit dem Neuen davor (RAD-136): grün die letzten 24 Stunden, gelb 7 Tage, blau 30 Tage; ohne Einheit,
  // die Farbe sagt die Zeit, der Hinweis nennt sie. Am Abo nur die jüngste Stufe (3/53), insgesamt alle drei.
  import { t } from "../../lib/i18n.svelte.js";
  import { juengste, neues, STUFEN } from "../../lib/podcasts/neues";
  import type { Abo } from "../../lib/podcasts";

  let { abos, alle = false }: { abos: Abo[]; alle?: boolean } = $props();

  const n = $derived(neues(abos));
  const stufen = $derived(alle ? STUFEN : [juengste(n)].filter((s) => s !== null));
  const zahl = (x: number) => x.toLocaleString("de-DE", { useGrouping: false });
</script>

<span class="rh-zahl rh-neuzahl">
  {#each stufen as s (s)}<strong class="rh-neu-{s}" title={t(`podcastAnsicht.neues.${s}`, { n: n[s] })}>{zahl(n[s])}</strong><i aria-hidden="true">/</i>{/each}<span title={t("podcastAnsicht.ungehoert")}>{n.ungehoert || stufen.length ? zahl(n.ungehoert) : ""}</span>
</span>
