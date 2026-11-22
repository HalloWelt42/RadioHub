<script lang="ts" module>
  export type Chip = { art: string; titel: string; text: string; weg: () => void };
</script>

<script lang="ts">
  // Werkzeugleiste der Aufnahmen (Entwurf aufnahmen.html), dieselben Bausteine wie bei Radio und Podcasts: Knopf
  // Ordner (unter 1100 Pixeln), Zählwerk (Aufnahmen für die Auswahl oder Dateien des Ordners), Suche mit eigenem
  // Verlauf, Aktualisieren; darunter die aktiven Filter als Chips und der Hinweis, wohin neue Aufnahmen gehen.
  import { t } from "../../lib/i18n.svelte.js";
  import { zahl } from "../../lib/radio/anzeige";
  import { Suchverlauf } from "../../lib/radio/suchverlauf";
  import Suchfeld from "../radio/Suchfeld.svelte";

  const verlaufAufnahmen = new Suchverlauf("radiohub_aufnahmen_suche");
  const verlaufWolke = new Suchverlauf("radiohub_wolke_suche");

  let { wolke, anzahl, zusatz, suche, chips, ziel, nimmtAuf, laedt, leisteOffen, onsuche, onleiste, onaktualisieren }: {
    wolke: boolean;
    anzahl: number | null;
    zusatz: string;
    suche: string;
    chips: Chip[];
    /** Name des Ordners neuer Aufnahmen */
    ziel: string;
    nimmtAuf: boolean;
    laedt: boolean;
    leisteOffen: boolean;
    onsuche: (s: string) => void;
    onleiste: () => void;
    onaktualisieren: () => void;
  } = $props();
</script>

<div class="rh-werkzeug">
  <div class="rh-werkzeug-zeile">
    <button class="knopf rh-filter-auf" type="button" aria-expanded={leisteOffen} aria-controls="rh-aufnahmen-leiste" onclick={onleiste}>
      <i class="fa-solid fa-sliders"></i>{t("aufnahmenAnsicht.ordnerKnopf")}{#if chips.length}<span class="pille">{chips.length}</span>{/if}</button>
    <div class="rh-zaehler" title={wolke ? t("aufnahmenAnsicht.zaehlerWolkeHilfe") : t("aufnahmenAnsicht.zaehlerHilfe")}>
      <ak-segmente art="7" stellen="5" farbe="rot" text={anzahl === null ? "-----" : zahl(anzahl)}></ak-segmente>
      <span class="ak-etikett">{wolke ? t("aufnahmenAnsicht.dateien") : t("aufnahmenAnsicht.aufnahmen")}</span>
      {#if zusatz}<span class="rh-breit">{zusatz}</span>{/if}
    </div>
    {#key wolke}
      <Suchfeld wert={suche} gedaechtnis={wolke ? verlaufWolke : verlaufAufnahmen} name={wolke ? "wolke-suche" : "aufnahmen-suche"}
                platzhalter={wolke ? t("aufnahmenAnsicht.wolkeSuche") : t("aufnahmenAnsicht.suche")}
                beschriftung={wolke ? t("aufnahmenAnsicht.wolkeSuche") : t("aufnahmenAnsicht.suche")}
                hilfe={wolke ? t("aufnahmenAnsicht.wolkeSuche") : t("aufnahmenAnsicht.suche")} {onsuche} />
    {/key}
    <button class="knopf" type="button" title={t("aufnahmenAnsicht.aktualisierenHilfe")} aria-label={t("aufnahmenAnsicht.aktualisieren")} disabled={laedt}
            onclick={() => { onaktualisieren(); }}>
      <i class="fa-solid fa-rotate" class:fa-spin={laedt}></i><span class="rh-breit">{t("aufnahmenAnsicht.aktualisieren")}</span></button>
  </div>
  <div class="rh-werkzeug-zeile">
    <div class="rh-aktiv-chips" aria-label={t("aufnahmenAnsicht.aktiveFilter")}>
      {#each chips as c (c.art)}
        <span class="chip">{c.titel}: <b>{c.text}</b><button type="button" aria-label={t("aufnahmenAnsicht.filterEntfernen")}
              title={t("aufnahmenAnsicht.filterEntfernen")} onclick={c.weg}><i class="fa-solid fa-xmark"></i></button></span>
      {:else}
        <span class="rh-leer-chips">{wolke ? t("aufnahmenAnsicht.alleDateien") : t("aufnahmenAnsicht.alleFilter")}</span>
      {/each}
    </div>
    <p class="rh-hinweis">
      {#if wolke}
        <i class="fa-solid fa-scissors"></i><span>{t("aufnahmenAnsicht.wolkeNeben")}</span>
      {:else}
        <span>{t("aufnahmenAnsicht.zielLeiste", { name: "" })}<b>{ziel}</b></span>
      {/if}
    </p>
  </div>
</div>
