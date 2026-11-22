<script lang="ts">
  // Kopf eines eigenen Ordners in der Seitenleiste (RAD-23): Klick klappt auf und zu, Stift benennt um (Eingabe an Ort
  // und Stelle, Enter übernimmt, Escape bricht ab), Papierkorb löst den Ordner auf. Auflösen fragt vorher und nennt die
  // Abos, die danach wieder lose stehen; es wird nichts abbestellt und nichts gelöscht. Der Kopf ist Ziel beim Ziehen:
  // ein Abo darauf kommt in den Ordner, ein Ordner darauf wird davor oder dahinter einsortiert (Platzhalter zeigt es).
  import { Rueckfrage } from "appkern-oberflaeche";
  import { t } from "../../lib/i18n.svelte.js";
  import type { Abo, Ordner } from "../../lib/podcasts";

  let { ordner, abos, ziel, ongriff, onende, onueber, onablegen, onumbenennen, onklappen, onloeschen }: {
    ordner: Ordner;
    /** die Abos des Ordners (ohne angeheftete) */
    abos: Abo[];
    /** dieser Kopf ist gerade Ziel eines gezogenen Abos */
    ziel: boolean;
    ongriff: (e: DragEvent) => void;
    onende: () => void;
    onueber: (e: DragEvent) => void;
    onablegen: (e: DragEvent) => void;
    onumbenennen: (name: string) => void;
    onklappen: () => void;
    onloeschen: () => Promise<void>;
  } = $props();

  const ungehoert = $derived(abos.reduce((s, a) => s + a.ungehoert, 0));
  let bearbeitet = $state(false);
  let name = $state("");
  let fragt = $state(false);
  let loescht = $state(false);

  function bearbeiten(e: Event) {
    e.stopPropagation();
    name = ordner.name;
    bearbeitet = true;
  }

  function uebernehmen() {
    const neu = name.trim();
    bearbeitet = false;
    if (neu && neu !== ordner.name) onumbenennen(neu);
  }

  async function loeschen() {
    loescht = true;
    try {
      await onloeschen();
      fragt = false;
    } finally {
      loescht = false;
    }
  }

  function fokus(el: HTMLInputElement) {
    el.focus();
    el.select();
  }
</script>

<div class="rh-facette rh-ordner" class:ziel class:zu={!ordner.offen} role="button" tabindex="0" aria-expanded={ordner.offen}
     title={t("podcastAnsicht.ordnerHilfe")}
     onclick={() => { if (!bearbeitet) onklappen(); }}
     onkeydown={(e) => { if (!bearbeitet && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); onklappen(); } }}
     ondragover={onueber} ondrop={onablegen}>
  <span class="rh-griff" draggable="true" title={t("podcastAnsicht.ordnerZiehenHilfe")} aria-hidden="true" ondragstart={ongriff} ondragend={onende}>
    <i class="fa-solid fa-grip-vertical"></i></span>
  <i class="fa-solid fa-chevron-down rh-klappe" aria-hidden="true"></i>
  <i class="fa-solid {ordner.offen ? 'fa-folder-open' : 'fa-folder'} rh-ordner-symbol" aria-hidden="true"></i>
  {#if bearbeitet}
    <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
    <span class="rh-ordner-eingabe" onclick={(e) => e.stopPropagation()}>
      <input type="text" bind:value={name} maxlength="80" aria-label={t("podcastAnsicht.ordnerName")} use:fokus
             onkeydown={(e) => { e.stopPropagation(); if (e.key === "Enter") uebernehmen(); if (e.key === "Escape") bearbeitet = false; }}
             onblur={uebernehmen} />
    </span>
  {:else}
    <span class="rh-abo-name">{ordner.name}</span>
  {/if}
  <span class="rh-abo-ende">
    <span class="rh-zahl" title={t("podcastAnsicht.ungehoert")}>{ungehoert || ""}</span>
    <button class="rh-nadel" type="button" aria-label="{t('podcastAnsicht.ordnerUmbenennen')}: {ordner.name}" title={t("podcastAnsicht.ordnerUmbenennen")}
            onclick={bearbeiten}><i class="fa-solid fa-pen"></i></button>
    <button class="rh-nadel" type="button" aria-label="{t('podcastAnsicht.ordnerAufloesen')}: {ordner.name}" title={t("podcastAnsicht.ordnerAufloesen")}
            onclick={(e) => { e.stopPropagation(); fragt = true; }}><i class="fa-solid fa-trash-can rh-loeschen"></i></button>
  </span>
</div>
{#if fragt}
  <div class="rh-ordner-frage">
    <Rueckfrage frage={t("podcastAnsicht.ordnerAufloesenFrage", { name: ordner.name })}
                hinweis={abos.length ? t("podcastAnsicht.ordnerAufloesenHinweis", { abos: abos.map((a) => a.titel).join(", ") }) : t("podcastAnsicht.ordnerLeerHinweis")}
                knopf={t("podcastAnsicht.ordnerAufloesen")} beschaeftigt={loescht} onabbrechen={() => (fragt = false)} onja={() => void loeschen()} />
  </div>
{/if}
