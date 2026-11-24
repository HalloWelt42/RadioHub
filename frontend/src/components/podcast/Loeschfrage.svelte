<script lang="ts">
  // Rückfrage vor dem Löschen einer gespeicherten Folge: nennt jede Datei, die mit ihr in den Papierkorb kommt (die Folge, vertonte
  // Fassungen, Transkripte, RAD-26). Gelöscht wird erst, wenn die Liste da ist.
  import { Rueckfrage } from "appkern-oberflaeche";
  import { t } from "../../lib/i18n.svelte.js";
  import { megabyte } from "../../lib/podcasts/anzeige";
  import { podcastquelle, type Folge, type Folgendatei } from "../../lib/podcasts";

  let { folge, beschaeftigt, onabbrechen, onja }: { folge: Folge; beschaeftigt: boolean; onabbrechen: () => void; onja: () => void } = $props();

  let dateien = $state<Folgendatei[] | null>(null);
  let fehler = $state("");
  $effect(() => {
    void podcastquelle.dateien(folge.id).then((d) => (dateien = d)).catch((f: Error) => (fehler = f.message));
  });
  const groesse = $derived((dateien ?? []).reduce((summe, d) => summe + d.groesse, 0));
  const hinweis = $derived(dateien === null ? fehler || t("podcastAnsicht.laedt")
    : dateien.length > 1 ? t("podcastAnsicht.loeschenMehrere", { n: dateien.length, mb: megabyte(groesse), pfade: dateien.map((d) => d.pfad).join("\n") })
    : t("podcastAnsicht.loeschenHinweis", { pfad: dateien[0]?.pfad || folge.ablagePfad || folge.titel, mb: megabyte(groesse || folge.groesse) }));
</script>

<div class="rh-loeschfrage">
  <Rueckfrage frage={t("podcastAnsicht.loeschenFrage")} {hinweis} knopf={t("podcastAnsicht.loeschen")} beschaeftigt={beschaeftigt || dateien === null} {onabbrechen} {onja} />
</div>
