<script lang="ts">
  // Seitenleiste der Aufnahmen (Entwurf aufnahmen.html, RAD-17): oben die Quelle (eigene Aufnahmen oder die ganze
  // Kellerwolke). Aufnahmen: Ordner mit Zahl; rotes Licht und Kreis zeigen, wo neue Aufnahmen landen, ein Klick auf den
  // Kreis macht einen Ordner zum Ziel; umbenennen an Ort und Stelle; löschen nur leer und nach Rückfrage. Kellerwolke:
  // Pfad und Unterordner, Ebene für Ebene. Unten fest die Kennzahlen.
  import { Rueckfrage } from "appkern-oberflaeche";
  import { t } from "../../lib/i18n.svelte.js";
  import type { Aufnahmeansicht, Aufnahmeordner, Wolkenebene } from "../../lib/aufnahmen";

  let { ansicht, ordner, gesamt, ohneOrdner, ebene, wolkeFehler, kennzahlen, offen, wolkeMoeglich,
        onquelle, onordner, onziel, onumbenennen, onloeschen, onanlegen, onpfad, onzu }: {
    ansicht: Aufnahmeansicht;
    ordner: Aufnahmeordner[];
    gesamt: number | null;
    ohneOrdner: number | null;
    ebene: Wolkenebene | null;
    wolkeFehler: string;
    kennzahlen: { dateien: number; mb: number; freiGb: number } | null;
    offen: boolean;
    wolkeMoeglich: boolean;
    onquelle: (q: "aufnahmen" | "wolke") => void;
    onordner: (o: string) => void;
    onziel: (id: number | null) => void;
    onumbenennen: (id: number, name: string) => void;
    onloeschen: (id: number) => Promise<void>;
    onanlegen: (name: string) => void;
    onpfad: (pfad: string) => void;
    onzu: () => void;
  } = $props();

  let fragt = $state<number | null>(null);
  let bearbeitet = $state<number | null>(null);
  let name = $state("");
  let legtAn = $state(false);
  const zielOrdner = $derived(ordner.find((o) => o.ziel) ?? null);

  function fokus(el: HTMLInputElement) { el.focus(); el.select(); }
  function umbenennen(o: Aufnahmeordner) {
    const neu = name.trim();
    bearbeitet = null;
    if (neu && neu !== o.name) onumbenennen(o.id, neu);
  }
  function anlegen() {
    const neu = name.trim();
    legtAn = false;
    name = "";
    if (neu) onanlegen(neu);
  }
</script>

<aside class="rh-filter rh-a-leiste" class:offen id="rh-aufnahmen-leiste" aria-label={t("aufnahmenAnsicht.ordner")}>
  <div class="rh-filter-oben rh-folgen-wahl">
    <div class="segment rh-a-quelle" role="radiogroup" aria-label={t("aufnahmenAnsicht.quelle")}>
      <button type="button" class:aktiv={ansicht.quelle === "aufnahmen"} aria-pressed={ansicht.quelle === "aufnahmen"} onclick={() => onquelle("aufnahmen")}>
        <i class="fa-solid fa-circle-dot"></i>{t("aufnahmenAnsicht.aufnahmen")}</button>
      {#if wolkeMoeglich}
        <button type="button" class:aktiv={ansicht.quelle === "wolke"} aria-pressed={ansicht.quelle === "wolke"} title={t("aufnahmenAnsicht.quelleWolkeHilfe")}
                onclick={() => onquelle("wolke")}><i class="fa-solid fa-cloud"></i>{t("aufnahmenAnsicht.kellerwolke")}</button>
      {/if}
    </div>
    <button class="rh-kopf-taste rh-filter-zu" type="button" aria-label={t("radio.schliessen")} title={t("radio.schliessen")} onclick={onzu}><i class="fa-solid fa-xmark"></i></button>
  </div>

  <div class="rh-filter-rollt">
    {#if ansicht.quelle === "aufnahmen"}
      <section class="rh-gruppe">
        <div class="rh-gruppe-kopf"><h3>{t("aufnahmenAnsicht.ordner")}</h3>
          <button type="button" onclick={() => { name = ""; legtAn = true; }}>{t("aufnahmenAnsicht.ordnerAnlegen")}</button></div>
        <div class="rh-facetten rh-abos">
          <button class="rh-facette rh-alle-abos" class:an={ansicht.ordner === ""} type="button" aria-pressed={ansicht.ordner === ""} onclick={() => onordner("")}>
            <span class="rh-abo-name">{t("aufnahmenAnsicht.alleAufnahmen")}</span><span class="rh-zahl">{gesamt ?? ""}</span></button>
          {#if legtAn}
            <span class="rh-ordner-eingabe rh-ordner-neu"><i class="fa-solid fa-folder-plus" aria-hidden="true"></i>
              <input type="text" bind:value={name} maxlength="80" placeholder={t("aufnahmenAnsicht.ordnerName")} aria-label={t("aufnahmenAnsicht.ordnerName")} use:fokus
                     onkeydown={(e) => { if (e.key === "Enter") anlegen(); if (e.key === "Escape") legtAn = false; }} onblur={anlegen} /></span>
          {/if}
          {#each ordner as o (o.id)}
            <div class="rh-facette rh-aordner" class:an={ansicht.ordner === String(o.id)} role="button" tabindex="0" aria-pressed={ansicht.ordner === String(o.id)}
                 onclick={() => { if (bearbeitet !== o.id) onordner(String(o.id)); }}
                 onkeydown={(e) => { if (bearbeitet !== o.id && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); onordner(String(o.id)); } }}>
              <i class="fa-solid fa-folder rh-ordner-symbol" aria-hidden="true"></i>
              {#if bearbeitet === o.id}
                <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
                <span class="rh-ordner-eingabe" onclick={(e) => e.stopPropagation()}>
                  <input type="text" bind:value={name} maxlength="80" aria-label={t("aufnahmenAnsicht.ordnerName")} use:fokus
                         onkeydown={(e) => { e.stopPropagation(); if (e.key === "Enter") umbenennen(o); if (e.key === "Escape") bearbeitet = null; }} onblur={() => umbenennen(o)} /></span>
              {:else}<span class="rh-abo-name">{o.name}</span>{/if}
              <span class="rh-abo-ende"><span class="rh-zahl">{o.anzahl}</span>
                <button class="rh-nadel" class:an={o.ziel} type="button" aria-pressed={o.ziel} title={o.ziel ? t("aufnahmenAnsicht.istZiel") : t("aufnahmenAnsicht.ziel")}
                        aria-label="{t('aufnahmenAnsicht.ziel')}: {o.name}" onclick={(e) => { e.stopPropagation(); onziel(o.ziel ? null : o.id); }}><i class="fa-solid fa-circle-dot"></i></button>
                <button class="rh-nadel" type="button" title={t("aufnahmenAnsicht.umbenennen")} aria-label="{t('aufnahmenAnsicht.umbenennen')}: {o.name}"
                        onclick={(e) => { e.stopPropagation(); name = o.name; bearbeitet = o.id; }}><i class="fa-solid fa-pen"></i></button>
                <button class="rh-nadel" type="button" title={t("aufnahmenAnsicht.ordnerLoeschen")} aria-label="{t('aufnahmenAnsicht.ordnerLoeschen')}: {o.name}"
                        onclick={(e) => { e.stopPropagation(); fragt = o.id; }}><i class="fa-solid fa-trash-can rh-loeschen"></i></button></span>
            </div>
            {#if fragt === o.id}
              {#if o.anzahl}
                <p class="hinweis-band rh-leiste-hinweis"><i class="fa-solid fa-lock"></i><span>{t("aufnahmenAnsicht.ordnerVoll", { name: o.name, n: o.anzahl })}</span>
                  <button class="knopf" type="button" onclick={() => (fragt = null)}>{t("aufnahmenAnsicht.verstanden")}</button></p>
              {:else}
                <div class="rh-ordner-frage"><Rueckfrage frage={t("aufnahmenAnsicht.ordnerLoeschenFrage", { name: o.name })} knopf={t("aufnahmenAnsicht.loeschen")}
                  onabbrechen={() => (fragt = null)} onja={() => { fragt = null; void onloeschen(o.id); }} /></div>
              {/if}
            {/if}
          {/each}
          <div class="rh-facette rh-aordner" class:an={ansicht.ordner === "ohne"} role="button" tabindex="0" aria-pressed={ansicht.ordner === "ohne"}
               onclick={() => onordner("ohne")} onkeydown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onordner("ohne"); } }}>
            <i class="fa-solid fa-house rh-ordner-symbol" aria-hidden="true"></i><span class="rh-abo-name">{t("aufnahmenAnsicht.ohneOrdner")}</span>
            <span class="rh-abo-ende"><span class="rh-zahl">{ohneOrdner ?? ""}</span>
              <button class="rh-nadel" class:an={!zielOrdner} type="button" aria-pressed={!zielOrdner} title={!zielOrdner ? t("aufnahmenAnsicht.istZiel") : t("aufnahmenAnsicht.ziel")}
                      aria-label="{t('aufnahmenAnsicht.ziel')}: {t('aufnahmenAnsicht.ohneOrdner')}" onclick={(e) => { e.stopPropagation(); onziel(null); }}><i class="fa-solid fa-circle-dot"></i></button></span>
          </div>
        </div>
      </section>
    {:else}
      <section class="rh-gruppe">
        <div class="rh-gruppe-kopf"><h3>{t("aufnahmenAnsicht.kellerwolke")}</h3></div>
        <nav class="rh-wolke-pfad" aria-label={t("aufnahmenAnsicht.kellerwolke")}>
          <button type="button" aria-current={!ansicht.pfad ? "page" : undefined} onclick={() => onpfad("")}><i class="fa-solid fa-cloud"></i>{t("aufnahmenAnsicht.wolkeWurzel")}</button>
          {#each ebene?.kette ?? [] as k, i (k.pfad)}
            <i class="fa-solid fa-chevron-right" aria-hidden="true"></i>
            <button type="button" aria-current={i === (ebene?.kette.length ?? 0) - 1 ? "page" : undefined} onclick={() => onpfad(k.pfad)}>{k.name}</button>
          {/each}
        </nav>
        <div class="rh-facetten rh-abos">
          {#if ansicht.pfad}
            <div class="rh-facette rh-aordner" role="button" tabindex="0" onclick={() => onpfad((ebene?.kette ?? []).slice(-2, -1)[0]?.pfad ?? "")}
                 onkeydown={(e) => { if (e.key === "Enter") onpfad((ebene?.kette ?? []).slice(-2, -1)[0]?.pfad ?? ""); }}>
              <span></span><i class="fa-solid fa-turn-up rh-ordner-symbol" aria-hidden="true"></i><span class="rh-abo-name">{t("aufnahmenAnsicht.wolkeEbeneHoeher")}</span><span></span></div>
          {/if}
          {#each ebene?.ordner ?? [] as o (o.pfad)}
            <div class="rh-facette rh-aordner" role="button" tabindex="0" onclick={() => onpfad(o.pfad)} onkeydown={(e) => { if (e.key === "Enter") onpfad(o.pfad); }}>
              <span></span><i class="fa-solid fa-folder rh-ordner-symbol" aria-hidden="true"></i><span class="rh-abo-name">{o.name}</span><span></span></div>
          {/each}
        </div>
        <p class="rh-still rh-abos-hinweis"><i class="fa-solid fa-circle-info"></i>{t("aufnahmenAnsicht.wolkeNurAudio")} {ebene?.schreibbar === false && ansicht.pfad ? t("aufnahmenAnsicht.wolkeEigen") : t("aufnahmenAnsicht.wolkeNeben")}</p>
      </section>
    {/if}
  </div>

  <div class="rh-leiste-fuss">
    {#if ansicht.quelle === "wolke"}
      <!-- der echte Stand: ohne Freigabe steht der Grund in der Mitte, hier nur, dass das Lesen fehlt -->
      {#if wolkeFehler}<span><i class="fa-solid fa-lock"></i> {t("aufnahmenAnsicht.wolkeKeinRecht")}</span>
      {:else}<span><i class="fa-solid fa-lock-open"></i> {t("aufnahmenAnsicht.wolkeRecht")}</span>{/if}
    {:else if kennzahlen}
      <span><b>{kennzahlen.dateien.toLocaleString("de-DE")}</b> {t("aufnahmenAnsicht.dateien")}</span>
      <span><b>{Math.round(kennzahlen.mb).toLocaleString("de-DE")}</b> MB</span>
      <span><b>{Math.round(kennzahlen.freiGb).toLocaleString("de-DE")}</b> {t("aufnahmenAnsicht.frei")}</span>
    {/if}
  </div>
</aside>
